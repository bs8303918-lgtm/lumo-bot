import asyncio
import json
import re
from datetime import datetime, timedelta, timezone

from urllib.parse import urlparse, urlunparse

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.models import Event, ProcessedPair, RawMessage, SentMatch, SystemState, User, UserChannel
from db.session import open_db_session


def normalize_channel_identifier(raw: str) -> str:
    text = raw.strip()
    text = text.replace("https://", "").replace("http://", "")
    text = text.replace("t.me/", "").replace("telegram.me/", "")
    if text.startswith("@"):
        text = text[1:]
    text = text.split("/")[0].split("?")[0]
    return text.lower()


CHANNEL_PATTERN = re.compile(r"^[\w]{3,}$", re.UNICODE)

_PLACEHOLDER_URLS = frozenset(
    {
        "—",
        "-",
        "none",
        "null",
        "n/a",
        "ссылка",
        "ссылка на регистрацию",
        "link",
        "registration link",
    }
)


def normalize_application_url(url: str | None) -> str | None:
    if not url:
        return None
    text = url.strip()
    if not text:
        return None
    lower = text.lower()
    inner = lower.strip("[]()«»\"'")
    if lower in _PLACEHOLDER_URLS or inner in _PLACEHOLDER_URLS:
        return None
    # Текст-плейсхолдер от LLM, не URL
    if "://" not in lower and (" " in text or not any(ch in text for ch in ".:/")):
        return None
    if "://" in lower and ("[" in text or "]" in text):
        bracket_host = re.search(r"\[([^\]]+)\]", text)
        if bracket_host and (" " in bracket_host.group(1) or "." not in bracket_host.group(1)):
            return None
    try:
        if "://" not in text:
            if "." not in text:
                return None
            text = f"https://{text}"
        parsed = urlparse(text)
        if not parsed.netloc or " " in parsed.netloc:
            return None
        if not parsed.hostname or "." not in parsed.hostname:
            return None
        path = parsed.path.rstrip("/") or "/"
        return urlunparse((parsed.scheme or "https", parsed.netloc, path, "", "", ""))
    except ValueError:
        return None


def is_valid_channel_format(identifier: str) -> bool:
    return bool(CHANNEL_PATTERN.match(identifier))


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _is_lock_timeout(exc: DBAPIError) -> bool:
        orig = exc.orig
        if orig is not None and "LockNotAvailable" in type(orig).__name__:
            return True
        msg = str(exc).lower()
        return "lock timeout" in msg or "locknotavailable" in msg

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def _insert_user_postgres(
        self,
        telegram_id: int,
        username: str | None,
    ) -> tuple[User, bool]:
        stmt = (
            pg_insert(User)
            .values(
                telegram_id=telegram_id,
                username=username,
                notifications_enabled=True,
            )
            .on_conflict_do_nothing(index_elements=["telegram_id"])
            .returning(User.id)
        )
        result = await self.session.execute(stmt)
        new_id = result.scalar_one_or_none()
        if new_id is not None:
            user = await self.get_by_id(new_id)
            if user:
                return user, True
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            raise RuntimeError(f"Could not resolve user telegram_id={telegram_id}")
        return user, False

    async def _get_or_create_sqlite(
        self,
        telegram_id: int,
        username: str | None = None,
    ) -> tuple[User, bool]:
        values = {
            "telegram_id": telegram_id,
            "username": username,
            "notifications_enabled": True,
        }
        insert_stmt = (
            sqlite_insert(User)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["telegram_id"])
            .returning(User.id)
        )
        result = await self.session.execute(insert_stmt)
        new_id = result.scalar_one_or_none()
        created = new_id is not None
        if created:
            user = await self.get_by_id(new_id)
        else:
            user = await self.get_by_telegram_id(telegram_id)
        if not user:
            raise RuntimeError(f"Could not resolve user telegram_id={telegram_id}")
        if username and user.username != username:
            user.username = username
        if not user.notifications_enabled:
            user.notifications_enabled = True
        await self.session.commit()
        return user, created

    async def get_or_create(self, telegram_id: int, username: str | None = None) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            changed = False
            if username and user.username != username:
                user.username = username
                changed = True
            if not user.notifications_enabled:
                user.notifications_enabled = True
                changed = True
            if changed:
                await self.session.flush()
            return user, False

        if get_settings().is_sqlite:
            return await self._get_or_create_sqlite(telegram_id, username)

        last_error: DBAPIError | None = None
        for attempt in range(4):
            try:
                async with open_db_session() as ins_sess:
                    ins_repo = UserRepository(ins_sess)
                    _user, created = await ins_repo._insert_user_postgres(telegram_id, username)
                    await ins_sess.commit()
                attached = await self.get_by_telegram_id(telegram_id)
                if not attached:
                    raise RuntimeError(f"Could not resolve user telegram_id={telegram_id}")
                return attached, created
            except DBAPIError as exc:
                await self.session.rollback()
                existing = await self.get_by_telegram_id(telegram_id)
                if existing:
                    return existing, False
                if self._is_lock_timeout(exc) and attempt < 3:
                    last_error = exc
                    await asyncio.sleep(0.05 * (2**attempt))
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Could not resolve user telegram_id={telegram_id}")

    async def set_notifications_enabled(self, user_id: int, enabled: bool) -> None:
        user = await self.get_by_id(user_id)
        if user:
            user.notifications_enabled = enabled
            await self.session.flush()

    async def delete_user(self, user_id: int) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            return False
        await self.session.delete(user)
        await self.session.flush()
        return True

    async def find_by_username(self, username: str) -> User | None:
        normalized = username.lstrip("@").lower()
        result = await self.session.execute(
            select(User).where(func.lower(User.username) == normalized)
        )
        return result.scalar_one_or_none()

    async def set_interest(self, user: User, interest_query: str) -> User:
        user.interest_query = interest_query.strip()
        user.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return user

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(User))
        return result.scalar_one()

    async def count_with_interest(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(User)
            .where(User.interest_query.is_not(None))
            .where(User.interest_query != "")
        )
        return result.scalar_one()

    async def list_with_interests(self) -> list[User]:
        result = await self.session.execute(
            select(User)
            .where(User.interest_query.is_not(None))
            .where(User.interest_query != "")
            .order_by(User.updated_at.desc())
        )
        return list(result.scalars().all())

    async def count_new_since(self, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.created_at >= since)
        )
        return result.scalar_one()

    async def list_all(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.id))
        return list(result.scalars().all())

    async def get_users_for_channel(self, channel_identifier: str, include_seed: bool) -> list[User]:
        identifier = normalize_channel_identifier(channel_identifier)
        stmt = (
            select(User)
            .join(UserChannel, UserChannel.user_id == User.id)
            .where(UserChannel.channel_identifier == identifier)
            .where(User.interest_query.is_not(None))
            .where(User.interest_query != "")
        )
        result = await self.session.execute(stmt)
        users = list(result.scalars().unique().all())

        if include_seed:
            seed_stmt = select(User).where(User.interest_query.is_not(None)).where(User.interest_query != "")
            seed_result = await self.session.execute(seed_stmt)
            seed_users = list(seed_result.scalars().all())
            seen = {u.id for u in users}
            for u in seed_users:
                if u.id not in seen:
                    users.append(u)
        return users

    async def get_notification_recipients(self, channel_identifier: str, *, is_seed: bool) -> list[User]:
        """
        Кому слать уведомление по посту из канала:
        - есть подписчики через /add_channel → только они (даже если канал ещё и seed)
        - иначе seed → всем с интересами
        - иначе никому
        """
        personal = await self.get_users_for_channel(channel_identifier, include_seed=False)
        if personal:
            return personal
        if is_seed:
            result = await self.session.execute(
                select(User).where(User.interest_query.is_not(None)).where(User.interest_query != "")
            )
            return list(result.scalars().all())
        return []


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        event_type: str,
        user_id: int | None = None,
        related_id: int | None = None,
        metadata: dict | None = None,
    ) -> None:
        event = Event(
            user_id=user_id,
            event_type=event_type,
            related_id=related_id,
            metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
        )
        self.session.add(event)

    async def count_by_type_since(self, since: datetime) -> dict[str, int]:
        result = await self.session.execute(
            select(Event.event_type, func.count())
            .where(Event.created_at >= since)
            .group_by(Event.event_type)
        )
        return {row[0]: row[1] for row in result.all()}

    async def count_user_events_since(
        self, user_id: int, event_type: str, since: datetime
    ) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Event)
            .where(Event.user_id == user_id)
            .where(Event.event_type == event_type)
            .where(Event.created_at >= since)
        )
        return int(result.scalar_one())

    async def count_distinct_users_since(self, event_type: str, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count(func.distinct(Event.user_id)))
            .where(Event.event_type == event_type)
            .where(Event.created_at >= since)
            .where(Event.user_id.is_not(None))
        )
        return result.scalar_one()

    async def funnel_snapshot(self, since: datetime, *, recent_limit: int = 12) -> dict:
        from analytics.event_types import FUNNEL_EVENT_TYPES

        events = await self.count_by_type_since(since)
        users: dict[str, int] = {}
        for event_type in FUNNEL_EVENT_TYPES:
            users[event_type] = await self.count_distinct_users_since(event_type, since)

        stuck_no_interest = await self.session.execute(
            select(func.count())
            .select_from(User)
            .where((User.interest_query.is_(None)) | (User.interest_query == ""))
        )
        stuck_no_cards = await self.session.execute(
            select(func.count())
            .select_from(User)
            .where(User.interest_query.is_not(None))
            .where(User.interest_query != "")
            .where(
                ~User.id.in_(
                    select(SentMatch.user_id).where(SentMatch.user_id.is_not(None)).distinct()
                )
            )
        )

        recent_rows = await self.session.execute(
            select(Event, User.username, User.telegram_id)
            .outerjoin(User, Event.user_id == User.id)
            .where(Event.user_id.is_not(None))
            .order_by(Event.created_at.desc())
            .limit(recent_limit)
        )
        recent = []
        for event, username, telegram_id in recent_rows.all():
            meta = ""
            if event.metadata_json:
                try:
                    data = json.loads(event.metadata_json)
                    if isinstance(data, dict):
                        meta = ", ".join(f"{k}={v}" for k, v in data.items() if k != "text_preview")
                except json.JSONDecodeError:
                    pass
            user_ref = f"@{username}" if username else (f"id{telegram_id}" if telegram_id else "?")
            recent.append(
                {
                    "type": event.event_type,
                    "user": user_ref,
                    "at": event.created_at,
                    "meta": meta,
                }
            )

        return {
            "events": events,
            "users": users,
            "stuck": {
                "no_interest": stuck_no_interest.scalar_one(),
                "no_cards": stuck_no_cards.scalar_one(),
            },
            "recent": recent,
        }

    async def count_active_users_since(self, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count(func.distinct(SentMatch.user_id))).where(SentMatch.sent_at >= since)
        )
        return result.scalar_one()


class SystemStateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def set(self, key: str, value: str) -> None:
        result = await self.session.execute(select(SystemState).where(SystemState.key == key))
        row = result.scalar_one_or_none()
        if row:
            row.value = value
            row.updated_at = datetime.now(timezone.utc)
        else:
            self.session.add(SystemState(key=key, value=value))

    async def get(self, key: str, default: str | None = None) -> str | None:
        result = await self.session.execute(select(SystemState).where(SystemState.key == key))
        row = result.scalar_one_or_none()
        return row.value if row else default

    async def increment(self, key: str) -> int:
        current = await self.get(key, "0")
        new_val = int(current or 0) + 1
        await self.set(key, str(new_val))
        return new_val

    async def reset(self, key: str) -> None:
        await self.set(key, "0")

    @staticmethod
    def llm_min_raw_id_key(user_id: int) -> str:
        return f"llm_min_raw_id:{user_id}"

    async def get_llm_min_raw_id(self, user_id: int) -> int | None:
        value = await self.get(self.llm_min_raw_id_key(user_id))
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    async def set_llm_min_raw_id(self, user_id: int, raw_message_id: int) -> None:
        await self.set(self.llm_min_raw_id_key(user_id), str(max(raw_message_id, 0)))


class MatchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_processed(self, user_id: int, raw_message_id: int) -> bool:
        result = await self.session.execute(
            select(ProcessedPair.id).where(
                ProcessedPair.user_id == user_id,
                ProcessedPair.raw_message_id == raw_message_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def was_sent(self, user_id: int, raw_message_id: int) -> bool:
        result = await self.session.execute(
            select(SentMatch.id).where(
                SentMatch.user_id == user_id,
                SentMatch.raw_message_id == raw_message_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def was_sent_for_link(self, user_id: int, message_link: str) -> bool:
        result = await self.session.execute(
            select(SentMatch.id).where(
                SentMatch.user_id == user_id,
                SentMatch.message_link == message_link,
            )
        )
        return result.scalar_one_or_none() is not None

    async def was_sent_for_application_url(self, user_id: int, application_url: str | None) -> bool:
        normalized = normalize_application_url(application_url)
        if not normalized:
            return False
        result = await self.session.execute(
            select(SentMatch.application_url).where(
                SentMatch.user_id == user_id,
                SentMatch.application_url.is_not(None),
            )
        )
        for (stored_url,) in result.all():
            if normalize_application_url(stored_url) == normalized:
                return True
        return False

    async def is_done(self, user_id: int, raw_message_id: int) -> bool:
        return await self.is_processed(user_id, raw_message_id) or await self.was_sent(
            user_id, raw_message_id
        )

    async def backfill_processed_from_sent(self) -> int:
        """Пометить уже отправленные карточки как обработанные (после рестарта / смены интереса)."""
        result = await self.session.execute(
            select(SentMatch.user_id, SentMatch.raw_message_id).where(
                ~select(ProcessedPair.id)
                .where(
                    ProcessedPair.user_id == SentMatch.user_id,
                    ProcessedPair.raw_message_id == SentMatch.raw_message_id,
                )
                .exists()
            )
        )
        rows = result.all()
        for user_id, raw_message_id in rows:
            self.session.add(
                ProcessedPair(
                    user_id=user_id,
                    raw_message_id=raw_message_id,
                    is_relevant=True,
                    llm_response_json='{"backfill":"already_sent"}',
                )
            )
        if rows:
            await self.session.flush()
        return len(rows)

    async def clear_processed_for_user(self, user_id: int) -> int:
        result = await self.session.execute(
            delete(ProcessedPair).where(ProcessedPair.user_id == user_id)
        )
        return result.rowcount or 0

    async def mark_processed(
        self,
        user_id: int,
        raw_message_id: int,
        is_relevant: bool,
        llm_response_json: str | None = None,
    ) -> bool:
        if await self.is_processed(user_id, raw_message_id):
            return False
        self.session.add(
            ProcessedPair(
                user_id=user_id,
                raw_message_id=raw_message_id,
                is_relevant=is_relevant,
                llm_response_json=llm_response_json,
            )
        )
        return True

    async def create_sent_match(
        self,
        user_id: int,
        raw_message_id: int,
        data: dict,
    ) -> SentMatch:
        match = SentMatch(
            user_id=user_id,
            raw_message_id=raw_message_id,
            title=data["title"],
            opportunity_type=data["type"],
            deadline=data.get("deadline", "не указан"),
            description=data["description"],
            requirements=data.get("requirements"),
            source_channel_name=data["source_channel_name"],
            message_link=data["message_link"],
            application_url=data.get("application_url"),
        )
        self.session.add(match)
        await self.session.flush()
        return match

    async def count_sent_total(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(SentMatch))
        return result.scalar_one()

    async def count_sent_since(self, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(SentMatch).where(SentMatch.sent_at >= since)
        )
        return result.scalar_one()

    async def top_channels_by_matches(
        self, limit: int = 5, *, exclude_seed: bool = True
    ) -> list[tuple[str, int]]:
        from db.models import MonitoredChannel, RawMessage

        stmt = (
            select(SentMatch.source_channel_name, func.count())
            .join(RawMessage, SentMatch.raw_message_id == RawMessage.id)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .group_by(SentMatch.source_channel_name)
            .order_by(func.count().desc())
        )
        if exclude_seed:
            stmt = stmt.where(MonitoredChannel.is_seed.is_(False))
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_sent_match(self, match_id: int) -> SentMatch | None:
        result = await self.session.execute(select(SentMatch).where(SentMatch.id == match_id))
        return result.scalar_one_or_none()


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_max_raw_message_id(self) -> int:
        result = await self.session.execute(select(func.max(RawMessage.id)))
        return result.scalar_one_or_none() or 0

    async def count_recent_seed_messages(self, max_message_age_days: int = 14) -> int:
        from db.models import MonitoredChannel

        cutoff = datetime.now(timezone.utc) - timedelta(days=max_message_age_days)
        result = await self.session.execute(
            select(func.count())
            .select_from(RawMessage)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(MonitoredChannel.is_seed.is_(True))
            .where(RawMessage.fetched_at >= cutoff)
        )
        return result.scalar_one()

    async def count_seed_channels(self) -> int:
        from db.models import MonitoredChannel

        result = await self.session.execute(
            select(func.count())
            .select_from(MonitoredChannel)
            .where(MonitoredChannel.is_seed.is_(True))
        )
        return result.scalar_one()

    async def get_seed_onboarding_work(
        self,
        user_id: int,
        scan_limit: int = 10,
        max_message_age_days: int | None = None,
    ) -> list[tuple["RawMessage", User]]:
        """Недавние посты из seed-каналов — только если включён LLM pair relevance."""
        from db.models import MonitoredChannel
        from sqlalchemy import and_, or_
        from services.message_freshness import llm_max_message_age_days

        user = await UserRepository(self.session).get_by_id(user_id)
        if not user or not user.interest_query:
            return []

        days = max_message_age_days if max_message_age_days is not None else llm_max_message_age_days()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.session.execute(
            select(RawMessage)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(MonitoredChannel.is_seed.is_(True))
            .where(
                RawMessage.posted_at.is_not(None),
                RawMessage.posted_at >= cutoff,
            )
            .order_by(RawMessage.fetched_at.desc())
            .limit(scan_limit)
        )
        messages = list(result.scalars().all())
        match_repo = MatchRepository(self.session)
        pending: list[tuple[RawMessage, User]] = []

        for msg in messages:
            if await match_repo.is_done(user.id, msg.id):
                continue
            if await match_repo.was_sent_for_link(user.id, msg.message_link):
                continue
            pending.append((msg, user))

        return pending

    async def get_pending_work(
        self,
        scan_limit: int = 300,
        max_pairs: int = 40,
        user_id: int | None = None,
        max_message_age_days: int | None = None,
    ) -> list[tuple["RawMessage", User]]:
        """Сообщения × пользователи для LLM relevance (только свежие посты)."""
        from db.models import MonitoredChannel
        from sqlalchemy import and_, or_
        from services.message_freshness import llm_max_message_age_days

        days = max_message_age_days if max_message_age_days is not None else llm_max_message_age_days()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(RawMessage)
            .where(
                RawMessage.posted_at.is_not(None),
                RawMessage.posted_at >= cutoff,
            )
            .order_by(RawMessage.fetched_at.desc())
            .limit(scan_limit)
        )
        messages = list(result.scalars().all())
        match_repo = MatchRepository(self.session)
        user_repo = UserRepository(self.session)
        state_repo = SystemStateRepository(self.session)
        pending: list[tuple[RawMessage, User]] = []

        for msg in messages:
            ch_result = await self.session.execute(
                select(MonitoredChannel).where(MonitoredChannel.id == msg.monitored_channel_id)
            )
            channel = ch_result.scalar_one_or_none()
            if not channel:
                continue

            users = await user_repo.get_notification_recipients(
                channel.channel_identifier,
                is_seed=channel.is_seed,
            )
            for user in users:
                if user_id is not None and user.id != user_id:
                    continue
                if not user.interest_query:
                    continue
                min_raw_id = await state_repo.get_llm_min_raw_id(user.id)
                if min_raw_id is not None and msg.id <= min_raw_id:
                    continue
                if await match_repo.is_done(user.id, msg.id):
                    continue
                if await match_repo.was_sent_for_link(user.id, msg.message_link):
                    continue
                pending.append((msg, user))
                if len(pending) >= max_pairs:
                    return pending

        return pending

    async def count_pending_pairs(
        self,
        scan_limit: int = 300,
        max_message_age_days: int = 14,
        user_id: int | None = None,
    ) -> int:
        pending = await self.get_pending_work(
            scan_limit=scan_limit,
            max_pairs=10_000,
            user_id=user_id,
            max_message_age_days=max_message_age_days,
        )
        return len(pending)

    async def purge_expired_unmatched(self, batch_limit: int = 100) -> int:
        """Удалить просроченные посты без отправленных карточек."""
        from llm.deadline import is_opportunity_expired

        result = await self.session.execute(
            select(RawMessage).order_by(RawMessage.fetched_at.asc()).limit(batch_limit * 3)
        )
        removed = 0
        for msg in result.scalars().all():
            if removed >= batch_limit:
                break
            if not is_opportunity_expired(None, msg.text):
                continue
            sent = await self.session.execute(
                select(SentMatch.id).where(SentMatch.raw_message_id == msg.id).limit(1)
            )
            if sent.scalar_one_or_none():
                continue
            await self.session.delete(msg)
            removed += 1
        if removed:
            await self.session.flush()
        return removed

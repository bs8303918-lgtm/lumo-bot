import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes as orm_attributes, joinedload

from db.models import CatalogOpportunity, MonitoredChannel, RawMessage, User
from llm.deadline import is_opportunity_expired, resolve_entry_deadline
from llm.json_utils import coerce_llm_dict
from llm.spam_filter import (
    is_invalid_opportunity_extraction,
    is_likely_digest_or_roundup,
    is_likely_interview_or_rubric,
    is_likely_product_feature_news,
    is_likely_spam_or_ad,
)
from services.catalog_dedup import catalog_dedupe_keys
from services.catalog_freshness import filter_fresh_entries, is_unknown_deadline
from services.interest_matcher import (
    OPPORTUNITY_TYPES,
    build_opportunity_tags,
    entry_all_tags,
    tags_to_json,
    user_matches_type,
)
from services.opportunity_type import refine_opportunity_type
from services.message_freshness import (
    is_raw_message_too_old,
    is_raw_message_too_old_for_llm,
    llm_max_message_age_days,
    monitor_max_message_age_days,
    raw_message_anchor_date,
)


def parse_interest_categories(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).lower().strip() for x in data if x]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


class OpportunityCatalogRepository:
    def __init__(self, session: AsyncSession, *, no_deadline_max_age_days: int = 21):
        self.session = session
        self.no_deadline_max_age_days = no_deadline_max_age_days

    async def get_unclassified_messages(
        self, limit: int = 20, *, max_age_days: int | None = None
    ) -> list[tuple[RawMessage, MonitoredChannel]]:
        """Только свежие неклассифицированные посты (для LLM — по умолчанию llm_max_message_age_days)."""
        classified_ids = select(CatalogOpportunity.raw_message_id)
        days = max_age_days if max_age_days is not None else llm_max_message_age_days()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(RawMessage, MonitoredChannel)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(RawMessage.id.not_in(classified_ids))
            .where(RawMessage.posted_at.is_not(None))
            .where(RawMessage.posted_at >= cutoff)
            .order_by(RawMessage.posted_at.desc())
            .limit(limit)
        )
        return list(result.all())

    async def archive_stale_unclassified(
        self, *, max_age_days: int | None = None, limit: int = 100
    ) -> int:
        """Пометить старые посты как «не возможность» без вызова LLM."""
        days = max_age_days if max_age_days is not None else llm_max_message_age_days()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        classified_ids = select(CatalogOpportunity.raw_message_id)
        result = await self.session.execute(
            select(RawMessage, MonitoredChannel)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(RawMessage.id.not_in(classified_ids))
            .where(
                or_(
                    RawMessage.posted_at.is_(None),
                    RawMessage.posted_at < cutoff,
                )
            )
            .order_by(RawMessage.fetched_at.asc())
            .limit(limit)
        )
        archived = 0
        for raw_message, channel in result.all():
            await self.create(raw_message, channel, {"is_opportunity": False})
            archived += 1
        if archived:
            await self.session.flush()
        return archived

    async def find_active_duplicate(
        self,
        title: str | None,
        application_url: str | None,
        description: str | None,
    ) -> CatalogOpportunity | None:
        keys = catalog_dedupe_keys(title, application_url, description)
        if not keys:
            return None
        result = await self.session.execute(
            select(CatalogOpportunity).where(CatalogOpportunity.is_active.is_(True))
        )
        for entry in result.scalars():
            try:
                entry_keys = catalog_dedupe_keys(entry.title, entry.application_url, entry.description)
            except (ValueError, TypeError):
                continue
            if keys & entry_keys:
                return entry
        return None

    async def deactivate_duplicates(self) -> list[int]:
        """Оставить одну активную запись на название/ссылку — новее важнее."""
        result = await self.session.execute(
            select(CatalogOpportunity)
            .where(CatalogOpportunity.is_active.is_(True))
            .order_by(CatalogOpportunity.classified_at.desc())
        )
        seen_keys: set[str] = set()
        deactivated_ids: list[int] = []
        for entry in result.scalars():
            try:
                keys = catalog_dedupe_keys(entry.title, entry.application_url, entry.description)
            except (ValueError, TypeError):
                continue
            if not keys:
                continue
            if keys & seen_keys:
                entry.is_active = False
                deactivated_ids.append(entry.id)
                continue
            seen_keys |= keys
        if deactivated_ids:
            await self.session.flush()
        return deactivated_ids

    async def create(
        self,
        raw_message: RawMessage,
        channel: MonitoredChannel,
        data: dict,
    ) -> CatalogOpportunity:
        data = coerce_llm_dict(data) or {"is_opportunity": False}
        if not data.get("is_opportunity"):
            entry = CatalogOpportunity(
                raw_message_id=raw_message.id,
                opportunity_type="другое",
                title="—",
                deadline="не указан",
                description="",
                source_channel_name=channel.channel_title or channel.channel_identifier,
                message_link=raw_message.message_link,
                is_active=False,
            )
            self.session.add(entry)
            await self.session.flush()
            return entry

        invalid, _ = is_invalid_opportunity_extraction(data, raw_message.text)
        if invalid:
            entry = CatalogOpportunity(
                raw_message_id=raw_message.id,
                opportunity_type="другое",
                title="—",
                deadline="не указан",
                description="",
                source_channel_name=channel.channel_title or channel.channel_identifier,
                message_link=raw_message.message_link,
                is_active=False,
            )
            self.session.add(entry)
            await self.session.flush()
            return entry

        opp_type = refine_opportunity_type(raw_message.text, data.get("type"), data)
        if opp_type not in OPPORTUNITY_TYPES:
            opp_type = "другое"
        opp_tags = build_opportunity_tags(
            raw_message.text or "",
            title=data.get("title") or "",
            description=data.get("description") or "",
            requirements=data.get("requirements") or "",
            primary_type=opp_type,
            llm_tags=data.get("tags") if isinstance(data.get("tags"), list) else None,
        )
        tags_json = tags_to_json(opp_tags) if opp_tags else None
        deadline = data.get("deadline") or "не указан"
        anchor = raw_message_anchor_date(raw_message)
        deadline = resolve_entry_deadline(
            deadline,
            title=data.get("title") or "",
            description=(data.get("description") or raw_message.text or "")[:500],
            requirements=data.get("requirements") or "",
            anchor_date=anchor,
        )
        if is_raw_message_too_old(raw_message) or is_raw_message_too_old_for_llm(raw_message):
            entry = CatalogOpportunity(
                raw_message_id=raw_message.id,
                opportunity_type=opp_type,
                tags_json=tags_json,
                title=data.get("title") or "—",
                deadline=deadline,
                description=data.get("description") or "",
                source_channel_name=channel.channel_title or channel.channel_identifier,
                message_link=raw_message.message_link,
                is_active=False,
            )
            self.session.add(entry)
            await self.session.flush()
            return entry
        if is_opportunity_expired(deadline, raw_message.text, anchor_date=anchor):
            entry = CatalogOpportunity(
                raw_message_id=raw_message.id,
                opportunity_type=opp_type,
                tags_json=tags_json,
                title=data.get("title") or "—",
                deadline=deadline,
                description=data.get("description") or "",
                source_channel_name=channel.channel_title or channel.channel_identifier,
                message_link=raw_message.message_link,
                is_active=False,
            )
            self.session.add(entry)
            await self.session.flush()
            return entry

        title = data.get("title") or "Возможность"
        application_url = data.get("application_url")
        description = data.get("description") or raw_message.text[:500]

        duplicate = await self.find_active_duplicate(title, application_url, description)
        if duplicate:
            entry = CatalogOpportunity(
                raw_message_id=raw_message.id,
                opportunity_type=opp_type,
                tags_json=tags_json,
                title=title,
                deadline=deadline,
                description=description,
                requirements=data.get("requirements"),
                application_url=application_url,
                source_channel_name=channel.channel_title or channel.channel_identifier,
                message_link=raw_message.message_link,
                is_active=False,
            )
            self.session.add(entry)
            await self.session.flush()
            return entry

        entry = CatalogOpportunity(
            raw_message_id=raw_message.id,
            opportunity_type=opp_type,
            tags_json=tags_json,
            title=title,
            deadline=deadline,
            description=description,
            requirements=data.get("requirements"),
            application_url=application_url,
            source_channel_name=channel.channel_title or channel.channel_identifier,
            message_link=raw_message.message_link,
            is_active=True,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def create_manual_active(
        self,
        *,
        raw_message: RawMessage,
        channel: MonitoredChannel,
        opportunity_type: str,
        title: str,
        description: str,
        deadline: str,
        application_url: str | None = None,
        requirements: str | None = None,
    ) -> CatalogOpportunity:
        """Admin-approved user submission — skip LLM/spam pipeline."""
        raw_type = opportunity_type.lower().strip()
        custom_label: str | None = None
        if raw_type in OPPORTUNITY_TYPES:
            opp_type = raw_type
        else:
            custom_label = raw_type[:64]
            opp_type = "другое"

        source_blob = " ".join(filter(None, [title, description, requirements, raw_message.text or ""]))
        opp_tags = build_opportunity_tags(
            source_blob,
            title=title,
            description=description,
            requirements=requirements or "",
            primary_type=opp_type if opp_type != "другое" else (custom_label or "другое"),
        )
        if custom_label:
            opp_tags = [custom_label] + [t for t in opp_tags if t != custom_label]
            if opp_type == "другое" and len(opp_tags) == 1:
                opp_tags = [custom_label]
        entry = CatalogOpportunity(
            raw_message_id=raw_message.id,
            opportunity_type=opp_type,
            tags_json=tags_to_json(opp_tags) if opp_tags else None,
            title=title[:512],
            deadline=deadline or "не указан",
            description=description,
            requirements=requirements,
            application_url=application_url,
            source_channel_name=channel.channel_title or channel.channel_identifier,
            message_link=raw_message.message_link,
            is_active=True,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def count_active(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(CatalogOpportunity).where(CatalogOpportunity.is_active.is_(True))
        )
        return result.scalar_one()

    async def count_active_by_type(self) -> dict[str, int]:
        result = await self.session.execute(
            select(CatalogOpportunity.opportunity_type, func.count())
            .where(CatalogOpportunity.is_active.is_(True))
            .where(CatalogOpportunity.opportunity_type != "другое")
            .group_by(CatalogOpportunity.opportunity_type)
        )
        return {row[0]: row[1] for row in result.all()}

    async def _user_channel_identifiers(self, user_id: int) -> set[str]:
        from db.models import UserChannel

        result = await self.session.execute(
            select(UserChannel.channel_identifier).where(UserChannel.user_id == user_id)
        )
        return {row[0] for row in result.all()}

    def _catalog_access_condition(self, user_channel_ids: set[str]):
        if user_channel_ids:
            return or_(
                MonitoredChannel.is_seed.is_(True),
                MonitoredChannel.channel_identifier.in_(user_channel_ids),
            )
        return MonitoredChannel.is_seed.is_(True)

    async def count_active_for_user(self, user_id: int) -> int:
        user_channels = await self._user_channel_identifiers(user_id)
        result = await self.session.execute(
            select(CatalogOpportunity)
            .options(joinedload(CatalogOpportunity.raw_message))
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(CatalogOpportunity.is_active.is_(True))
            .where(self._catalog_access_condition(user_channels))
        )
        fresh = filter_fresh_entries(
            list(result.scalars().unique().all()),
            max_age_days_no_deadline=self.no_deadline_max_age_days,
        )
        return len(fresh)

    async def count_active_by_type_for_user(self, user_id: int) -> dict[str, int]:
        user_channels = await self._user_channel_identifiers(user_id)
        result = await self.session.execute(
            select(CatalogOpportunity)
            .options(joinedload(CatalogOpportunity.raw_message))
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(CatalogOpportunity.is_active.is_(True))
            .where(CatalogOpportunity.opportunity_type != "другое")
            .where(self._catalog_access_condition(user_channels))
        )
        fresh = filter_fresh_entries(
            list(result.scalars().unique().all()),
            max_age_days_no_deadline=self.no_deadline_max_age_days,
        )
        counts: dict[str, int] = {}
        for entry in fresh:
            for tag in entry_all_tags(entry):
                if tag != "другое":
                    counts[tag] = counts.get(tag, 0) + 1
        return counts

    async def get_active_for_user(
        self,
        user_id: int,
        types: list[str],
        limit: int = 60,
        *,
        extra_tags: list[str] | None = None,
    ) -> list[CatalogOpportunity]:
        if not types:
            types = list(OPPORTUNITY_TYPES)
        normalized = [t.lower().strip() for t in types]
        all_types = [t for t in OPPORTUNITY_TYPES if t != "другое"]
        filter_by_type = set(normalized) != set(all_types)
        extra_wanted = {t.lower().strip() for t in (extra_tags or []) if t}
        user_channels = await self._user_channel_identifiers(user_id)
        result = await self.session.execute(
            select(CatalogOpportunity)
            .options(joinedload(CatalogOpportunity.raw_message))
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(CatalogOpportunity.is_active.is_(True))
            .where(self._catalog_access_condition(user_channels))
            .order_by(CatalogOpportunity.classified_at.desc())
            .limit(limit * 4 if (filter_by_type or extra_wanted) else limit * 3)
        )
        fresh = filter_fresh_entries(
            list(result.scalars().unique().all()),
            max_age_days_no_deadline=self.no_deadline_max_age_days,
        )
        if filter_by_type or extra_wanted:
            wanted = set(normalized) if filter_by_type else set()

            def _matches(entry: CatalogOpportunity) -> bool:
                tags = set(entry_all_tags(entry))
                type_hit = bool(wanted & tags) if wanted else False
                extra_hit = bool(extra_wanted & tags) if extra_wanted else False
                if wanted and extra_wanted:
                    return type_hit or extra_hit
                if wanted:
                    return type_hit
                return extra_hit

            fresh = [e for e in fresh if _matches(e)]
        return fresh[:limit]

    async def list_all_active_for_user(
        self,
        user_id: int,
        types: list[str],
        *,
        max_rows: int = 5000,
    ) -> list[CatalogOpportunity]:
        """All fresh catalog rows for the user (for sorted/paginated Mini App lists)."""
        if not types:
            types = list(OPPORTUNITY_TYPES)
        normalized = [t.lower().strip() for t in types]
        all_types = [t for t in OPPORTUNITY_TYPES if t != "другое"]
        filter_by_type = set(normalized) != set(all_types)
        user_channels = await self._user_channel_identifiers(user_id)
        result = await self.session.execute(
            select(CatalogOpportunity)
            .options(joinedload(CatalogOpportunity.raw_message))
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(CatalogOpportunity.is_active.is_(True))
            .where(self._catalog_access_condition(user_channels))
            .order_by(CatalogOpportunity.classified_at.desc())
            .limit(max_rows)
        )
        fresh = filter_fresh_entries(
            list(result.scalars().unique().all()),
            max_age_days_no_deadline=self.no_deadline_max_age_days,
        )
        if filter_by_type:
            wanted = set(normalized)
            fresh = [e for e in fresh if wanted & set(entry_all_tags(e))]
        return fresh

    async def user_can_access_entry(self, user_id: int, entry_id: int) -> bool:
        user_channels = await self._user_channel_identifiers(user_id)
        result = await self.session.execute(
            select(CatalogOpportunity.id)
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(CatalogOpportunity.id == entry_id)
            .where(CatalogOpportunity.is_active.is_(True))
            .where(self._catalog_access_condition(user_channels))
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def list_all_public_active(
        self,
        *,
        max_rows: int = 5000,
    ) -> list[CatalogOpportunity]:
        """All active catalog rows (for Startify export — no user channel filter)."""
        result = await self.session.execute(
            select(CatalogOpportunity)
            .options(joinedload(CatalogOpportunity.raw_message))
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .where(CatalogOpportunity.is_active.is_(True))
            .where(CatalogOpportunity.opportunity_type != "другое")
            .order_by(CatalogOpportunity.classified_at.desc())
            .limit(max_rows)
        )
        return filter_fresh_entries(
            list(result.scalars().unique().all()),
            max_age_days_no_deadline=self.no_deadline_max_age_days,
        )

    async def get_active_for_domain(
        self,
        user_id: int,
        domain: str,
        limit: int = 3,
    ) -> list[CatalogOpportunity]:
        import re

        from services.interest_domains import DOMAIN_TAG_RULES

        slug = domain.lower().strip()
        patterns = [pat for pat, label in DOMAIN_TAG_RULES if label == slug]
        user_channels = await self._user_channel_identifiers(user_id)
        result = await self.session.execute(
            select(CatalogOpportunity)
            .options(joinedload(CatalogOpportunity.raw_message))
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(CatalogOpportunity.is_active.is_(True))
            .where(self._catalog_access_condition(user_channels))
            .order_by(CatalogOpportunity.classified_at.desc())
            .limit(120)
        )
        fresh = filter_fresh_entries(
            list(result.scalars().unique().all()),
            max_age_days_no_deadline=self.no_deadline_max_age_days,
        )
        matched: list[CatalogOpportunity] = []
        for entry in fresh:
            blob = " ".join(
                filter(
                    None,
                    [
                        entry.title,
                        entry.description,
                        entry.requirements,
                        " ".join(entry_all_tags(entry)),
                    ],
                )
            ).lower()
            if slug in blob or any(re.search(pat, blob, flags=re.I) for pat in patterns):
                matched.append(entry)
            if len(matched) >= limit:
                break
        return matched

    async def get_entry_with_channel(
        self, catalog_id: int
    ) -> tuple[CatalogOpportunity, MonitoredChannel] | None:
        result = await self.session.execute(
            select(CatalogOpportunity, MonitoredChannel, RawMessage)
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(CatalogOpportunity.id == catalog_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        entry, channel, raw_message = row
        orm_attributes.set_committed_value(entry, "raw_message", raw_message)
        return entry, channel

    async def get_active_for_types(self, types: list[str], limit: int = 30) -> list[CatalogOpportunity]:
        if not types:
            types = list(OPPORTUNITY_TYPES)
        normalized = [t.lower().strip() for t in types]
        filter_by_type = set(normalized) != set(OPPORTUNITY_TYPES)
        result = await self.session.execute(
            select(CatalogOpportunity)
            .where(CatalogOpportunity.is_active.is_(True))
            .order_by(CatalogOpportunity.classified_at.desc())
            .limit(limit * 4 if filter_by_type else limit)
        )
        entries = list(result.scalars().all())
        if filter_by_type:
            wanted = set(normalized)
            entries = [e for e in entries if wanted & set(entry_all_tags(e))]
        return entries[:limit]

    async def get_by_id(self, catalog_id: int) -> CatalogOpportunity | None:
        result = await self.session.execute(
            select(CatalogOpportunity).where(CatalogOpportunity.id == catalog_id)
        )
        return result.scalar_one_or_none()

    async def deactivate_expired(self) -> list[int]:
        result = await self.session.execute(
            select(CatalogOpportunity, RawMessage.text, RawMessage.posted_at, RawMessage.fetched_at)
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .where(CatalogOpportunity.is_active.is_(True))
        )
        deactivated_ids: list[int] = []
        for entry, source_text, posted_at, fetched_at in result.all():
            anchor = posted_at.date() if posted_at is not None else None
            text = source_text or entry.description or ""
            if is_opportunity_expired(entry.deadline, text, anchor_date=anchor):
                entry.is_active = False
                deactivated_ids.append(entry.id)
        if deactivated_ids:
            await self.session.flush()
        return deactivated_ids

    async def deactivate_old_posts(self, max_age_days: int | None = None) -> list[int]:
        """Скрыть каталог по постам старше N дней (независимо от дедлайна)."""
        days = max_age_days if max_age_days is not None else monitor_max_message_age_days()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(CatalogOpportunity, RawMessage.posted_at, RawMessage.fetched_at)
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .where(CatalogOpportunity.is_active.is_(True))
        )
        deactivated_ids: list[int] = []
        for entry, posted_at, fetched_at in result.all():
            if posted_at is None:
                entry.is_active = False
                deactivated_ids.append(entry.id)
                continue
            ref = posted_at
            if ref.tzinfo is None:
                ref = ref.replace(tzinfo=timezone.utc)
            if ref < cutoff:
                entry.is_active = False
                deactivated_ids.append(entry.id)
        if deactivated_ids:
            await self.session.flush()
        return deactivated_ids

    async def deactivate_stale_without_deadline(self) -> list[int]:
        """Hide old posts with no deadline (e.g. April announcements still marked active)."""
        result = await self.session.execute(
            select(CatalogOpportunity, RawMessage.posted_at, RawMessage.fetched_at)
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .where(CatalogOpportunity.is_active.is_(True))
        )
        deactivated_ids: list[int] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.no_deadline_max_age_days)
        for entry, posted_at, fetched_at in result.all():
            if posted_at is None:
                entry.is_active = False
                deactivated_ids.append(entry.id)
                continue
            post_date = posted_at
            anchor = post_date.date() if post_date else None
            if not is_unknown_deadline(entry.deadline, anchor_date=anchor):
                continue
            if is_opportunity_expired(entry.deadline, entry.description or "", anchor_date=anchor):
                entry.is_active = False
                deactivated_ids.append(entry.id)
                continue
            if post_date.tzinfo is None:
                post_date = post_date.replace(tzinfo=timezone.utc)
            if post_date < cutoff:
                entry.is_active = False
                deactivated_ids.append(entry.id)
        if deactivated_ids:
            await self.session.flush()
        return deactivated_ids

    async def deactivate_invalid_active(self) -> list[int]:
        result = await self.session.execute(
            select(CatalogOpportunity, RawMessage.text)
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .where(CatalogOpportunity.is_active.is_(True))
        )
        deactivated_ids: list[int] = []
        for entry, source_text in result.all():
            invalid, _ = is_invalid_opportunity_extraction(
                {
                    "is_opportunity": True,
                    "title": entry.title,
                    "description": entry.description,
                    "application_url": entry.application_url,
                },
                source_text,
            )
            if invalid:
                entry.is_active = False
                deactivated_ids.append(entry.id)
                continue
            is_digest, _ = is_likely_digest_or_roundup(source_text or "")
            if is_digest:
                entry.is_active = False
                deactivated_ids.append(entry.id)
                continue
            is_rubric, _ = is_likely_interview_or_rubric(source_text or "")
            if is_rubric:
                entry.is_active = False
                deactivated_ids.append(entry.id)
                continue
            is_product_news, _ = is_likely_product_feature_news(source_text or "")
            if is_product_news:
                entry.is_active = False
                deactivated_ids.append(entry.id)
                continue
            title_lower = (entry.title or "").lower()
            if title_lower.startswith("test ") or "test hackathon" in title_lower:
                entry.is_active = False
                deactivated_ids.append(entry.id)
        if deactivated_ids:
            await self.session.flush()
        return deactivated_ids

    async def reclassify_active_types(self) -> int:
        """Fix misclassified types and rebuild multi-tags for active entries."""
        result = await self.session.execute(
            select(CatalogOpportunity, RawMessage.text)
            .join(RawMessage, CatalogOpportunity.raw_message_id == RawMessage.id)
            .where(CatalogOpportunity.is_active.is_(True))
        )
        updated = 0
        for entry, source_text in result.all():
            new_type = refine_opportunity_type(
                source_text or "",
                entry.opportunity_type,
                {
                    "type": entry.opportunity_type,
                    "title": entry.title,
                    "description": entry.description,
                },
            )
            new_tags = build_opportunity_tags(
                source_text or "",
                title=entry.title,
                description=entry.description or "",
                requirements=entry.requirements or "",
                primary_type=new_type,
            )
            new_json = tags_to_json(new_tags) if new_tags else None
            changed = False
            if new_type != entry.opportunity_type:
                entry.opportunity_type = new_type
                changed = True
            if entry.tags_json != new_json:
                entry.tags_json = new_json
                changed = True
            if changed:
                updated += 1
        if updated:
            await self.session.flush()
        return updated

    async def get_users_for_type(
        self,
        opportunity_type: str,
        opportunity_tags: list[str] | None = None,
    ) -> list[User]:
        opp_type = opportunity_type.lower().strip()
        result = await self.session.execute(
            select(User)
            .where(User.interest_query.is_not(None))
            .where(User.interest_query != "")
        )
        users = []
        for user in result.scalars().all():
            if user_matches_type(
                user.interest_query or "",
                user.interest_categories_json,
                opp_type,
                opportunity_tags,
            ):
                users.append(user)
        return users

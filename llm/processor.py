import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from config import get_settings
from db.base import async_session_factory
from db.models import MonitoredChannel, RawMessage
from db.repositories.users import EventRepository, MatchRepository, MessageRepository, SystemStateRepository
from llm.client import LLMClient
from llm.deadline import is_opportunity_expired
from services.message_freshness import raw_message_anchor_date
from llm.json_utils import coerce_llm_dict
from llm.spam_filter import is_invalid_opportunity_extraction, is_likely_spam_or_ad
from logging_setup import log_error
from services.match_digest import get_digest_buffer
from services.notification_service import NotificationService, digest_cooldown_active
from services.opportunity_catalog import OpportunityCatalogService
from services.training_collector import record_relevance_llm

logger = logging.getLogger(__name__)


class LLMProcessor:
    def __init__(self, notification_service: NotificationService):
        self.llm = LLMClient()
        self.notification_service = notification_service
        self.settings = get_settings()

    async def process_pending(
        self,
        user_id: int | None = None,
        max_pairs: int | None = None,
    ) -> int:
        if not self.llm.settings.llm_configured:
            logger.warning("LLM API key not set, skipping LLM processing")
            return 0

        pair_limit = max_pairs if max_pairs is not None else self.settings.llm_max_pairs_per_cycle

        catalog_service = OpportunityCatalogService(self.notification_service)
        new_catalog_ids = await catalog_service.classify_pending()
        for catalog_id in new_catalog_ids:
            try:
                await catalog_service.notify_users_for_catalog_item(catalog_id)
            except Exception as exc:
                log_error(logger, "catalog_notify", exc, {"catalog_id": catalog_id})

        if not self.settings.llm_enable_pair_relevance:
            async with async_session_factory() as session:
                await SystemStateRepository(session).set(
                    "llm_processor_last_run_at",
                    datetime.now(timezone.utc).isoformat(),
                )
                await session.commit()
            if new_catalog_ids:
                logger.info("LLM cycle: classified %d posts (pair relevance off)", len(new_catalog_ids))
            return 0

        async with async_session_factory() as session:
            repo = MessageRepository(session)
            pending = await repo.get_pending_work(
                scan_limit=self.settings.llm_pending_scan_limit,
                max_pairs=pair_limit,
                user_id=user_id,
                max_message_age_days=self.settings.llm_max_message_age_days,
            )

        if not pending:
            logger.debug("LLM cycle: no pending user/message pairs")
            return 0

        logger.info("LLM cycle: %d pending pairs to check (по одному, с паузами)", len(pending))
        sent = 0
        touched_users: set[int] = set()
        for raw_message, user in pending:
            try:
                result = await self._process_pair(
                    user_id=user.id,
                    user_telegram_id=user.telegram_id,
                    interest_query=user.interest_query,
                    raw_message=raw_message,
                )
                if result is True:
                    sent += 1
                    touched_users.add(user.id)
            except Exception as exc:
                log_error(
                    logger,
                    "llm_processor",
                    exc,
                    {"user_id": user.id, "raw_message_id": raw_message.id},
                )

        await self._flush_buffered_digests(touched_users)

        async with async_session_factory() as session:
            await SystemStateRepository(session).set(
                "llm_processor_last_run_at",
                datetime.now(timezone.utc).isoformat(),
            )
            await session.commit()

        if sent:
            logger.info("LLM cycle: sent %d cards", sent)
        return sent

    async def process_user_backlog(self, user_id: int, max_pairs: int | None = None) -> int:
        return await self.process_pending(user_id=user_id, max_pairs=max_pairs)

    async def process_onboarding(
        self,
        user_id: int,
        *,
        max_pairs: int | None = None,
        on_progress=None,
    ) -> tuple[int, int]:
        """Приоритет: seed-каналы. Возвращает (отправлено карточек, просмотрено постов)."""
        if not self.llm.settings.llm_configured:
            logger.warning("LLM API key not set, skipping onboarding scan")
            return 0, 0

        pair_limit = max_pairs if max_pairs is not None else self.settings.llm_onboarding_max_pairs
        scan_limit = self.settings.llm_onboarding_seed_scan_limit

        async with async_session_factory() as session:
            msg_repo = MessageRepository(session)
            pending = await msg_repo.get_seed_onboarding_work(
                user_id,
                scan_limit=scan_limit,
                max_message_age_days=self.settings.monitor_initial_max_age_days,
            )

        if not pending:
            return 0, 0

        total = len(pending)
        sent = 0
        checked = 0
        for raw_message, user in pending:
            checked += 1
            if on_progress:
                try:
                    await on_progress(checked, total)
                except Exception:
                    pass
            try:
                result = await self._process_pair(
                    user_id=user.id,
                    user_telegram_id=user.telegram_id,
                    interest_query=user.interest_query,
                    raw_message=raw_message,
                )
                if result is True:
                    sent += 1
            except Exception as exc:
                log_error(
                    logger,
                    "llm_onboarding",
                    exc,
                    {"user_id": user.id, "raw_message_id": raw_message.id},
                )
            if sent >= pair_limit:
                break

        if sent < pair_limit:
            extra = await self.process_pending(
                user_id=user_id,
                max_pairs=pair_limit - sent,
            )
            sent += extra
        else:
            await self._flush_buffered_digests({user_id})

        return sent, checked

    async def _flush_buffered_digests(self, user_ids: set[int]) -> None:
        if not user_ids:
            return
        cap = self.settings.notification_digest_max_flush
        for uid in user_ids:
            if get_digest_buffer().pending_count(uid) <= 0:
                continue
            if await digest_cooldown_active(uid):
                continue
            await self.notification_service.flush_user_digest(
                uid,
                flush_remaining=True,
                max_items=cap,
            )

    async def _process_pair(
        self,
        user_id: int,
        user_telegram_id: int,
        interest_query: str,
        raw_message: RawMessage,
    ) -> bool | None:
        """True = card sent, False = processed/skipped, None = LLM unavailable (retry later)."""
        async with async_session_factory() as session:
            match_repo = MatchRepository(session)
            if await match_repo.is_done(user_id, raw_message.id):
                return False
            if await match_repo.was_sent_for_link(user_id, raw_message.message_link):
                await match_repo.mark_processed(
                    user_id,
                    raw_message.id,
                    True,
                    '{"dedup":"already_sent"}',
                )
                await session.commit()
                return False

        async with async_session_factory() as session:
            ch_result = await session.execute(
                select(MonitoredChannel).where(MonitoredChannel.id == raw_message.monitored_channel_id)
            )
            channel = ch_result.scalar_one()

        is_spam, spam_reason = is_likely_spam_or_ad(raw_message.text)
        if is_spam:
            logger.info(
                "Skipping spam/ad (%s) for user %s, message %s",
                spam_reason,
                user_id,
                raw_message.id,
            )
            async with async_session_factory() as session:
                match_repo = MatchRepository(session)
                await match_repo.mark_processed(
                    user_id,
                    raw_message.id,
                    False,
                    json.dumps({"relevant": False, "filtered": spam_reason}, ensure_ascii=False),
                )
                await session.commit()
            return False

        data, raw_response = await self.llm.check_relevance(interest_query, raw_message.text)
        data = coerce_llm_dict(data)

        async with async_session_factory() as session:
            match_repo = MatchRepository(session)
            event_repo = EventRepository(session)

            if await match_repo.is_done(user_id, raw_message.id):
                return False
            if await match_repo.was_sent_for_link(user_id, raw_message.message_link):
                await match_repo.mark_processed(
                    user_id,
                    raw_message.id,
                    True,
                    '{"dedup":"already_sent"}',
                )
                await session.commit()
                return False

            if data is None:
                await event_repo.log("llm_error", user_id=user_id, related_id=raw_message.id)
                await session.commit()
                return None

            is_relevant = bool(data.get("relevant"))
            invalid, inv_reason = is_invalid_opportunity_extraction(
                {"is_opportunity": is_relevant, **(data or {})},
                raw_message.text,
            )
            if invalid:
                logger.info(
                    "Skipping invalid opportunity (%s) for user %s, message %s",
                    inv_reason,
                    user_id,
                    raw_message.id,
                )
                is_relevant = False
                llm_json = json.dumps(
                    {"relevant": False, "filtered": inv_reason},
                    ensure_ascii=False,
                )
            else:
                llm_json = json.dumps(data, ensure_ascii=False)

            deadline = data.get("deadline")
            if is_relevant and is_opportunity_expired(
                deadline, raw_message.text, anchor_date=raw_message_anchor_date(raw_message)
            ):
                logger.info(
                    "Skipping expired opportunity (deadline=%s) for user %s, message %s",
                    deadline,
                    user_id,
                    raw_message.id,
                )
                is_relevant = False

            application_url = data.get("application_url")

            if is_relevant and await match_repo.was_sent_for_link(user_id, raw_message.message_link):
                llm_json = '{"dedup":"already_sent"}'
                is_relevant = False
            elif is_relevant and await match_repo.was_sent_for_application_url(user_id, application_url):
                llm_json = '{"dedup":"same_application_url"}'
                is_relevant = False
                logger.info(
                    "Skipping duplicate event URL for user %s, message %s",
                    user_id,
                    raw_message.id,
                )

            try:
                await match_repo.mark_processed(
                    user_id, raw_message.id, is_relevant, llm_json
                )
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return False

        await record_relevance_llm(
            user_id=user_id,
            interest_query=interest_query or "",
            raw_message=raw_message,
            channel=channel,
            llm_output=data if isinstance(data, dict) else {},
            relevant=is_relevant,
            model_name=self.settings.llm_model_name,
        )

        if not is_relevant:
            return False

        card_data = {
            "title": data.get("title") or "Возможность",
            "type": data.get("type") or "другое",
            "deadline": data.get("deadline") or "не указан",
            "description": data.get("description") or raw_message.text[:500],
            "requirements": data.get("requirements"),
            "source_channel_name": channel.channel_title or channel.channel_identifier,
            "message_link": raw_message.message_link,
            "application_url": data.get("application_url"),
        }

        async with async_session_factory() as session:
            match_repo = MatchRepository(session)
            event_repo = EventRepository(session)
            state_repo = SystemStateRepository(session)

            if await match_repo.was_sent_for_link(user_id, raw_message.message_link):
                return False
            if await match_repo.was_sent_for_application_url(user_id, card_data.get("application_url")):
                return False

            try:
                sent = await match_repo.create_sent_match(user_id, raw_message.id, card_data)
                await event_repo.log("card_sent", user_id=user_id, related_id=sent.id)
                await state_repo.set("llm_api_ok", "true")
                await session.commit()
            except IntegrityError:
                await session.rollback()
                logger.info(
                    "Card already sent for user %s, message %s — skipping duplicate",
                    user_id,
                    raw_message.id,
                )
                return False

        delivered = await self.notification_service.enqueue_match(
            user_id=user_id,
            telegram_id=user_telegram_id,
            match_id=sent.id,
            card_data=card_data,
            flush_remaining=False,
            auto_flush=False,
        )
        if not delivered:
            async with async_session_factory() as session:
                from db.repositories.users import UserRepository

                await UserRepository(session).set_notifications_enabled(user_id, False)
                await session.commit()
            return False
        return True

    async def run_forever(self, interval_seconds: int | None = None) -> None:
        import asyncio

        if interval_seconds is None:
            interval_seconds = self.llm.settings.llm_processor_interval_seconds

        await self._wait_restart_cooldown(interval_seconds)

        while True:
            try:
                await self.process_pending()
            except Exception as exc:
                log_error(logger, "llm_processor", exc)
            await asyncio.sleep(interval_seconds)

    async def _wait_restart_cooldown(self, interval_seconds: int) -> None:
        import asyncio

        cooldown = self.settings.llm_restart_cooldown_seconds
        async with async_session_factory() as session:
            state_repo = SystemStateRepository(session)
            last_run = await state_repo.get("llm_processor_last_run_at")
        if not last_run:
            return
        try:
            last_dt = datetime.fromisoformat(last_run)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return
        elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
        wait = min(cooldown, interval_seconds) - elapsed
        if wait > 0:
            logger.info(
                "LLM processor: жду %.0f сек после перезапуска (не слать пачку сразу)",
                wait,
            )
            await asyncio.sleep(wait)

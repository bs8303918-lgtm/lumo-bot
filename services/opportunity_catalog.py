import json
import logging

from sqlalchemy.exc import IntegrityError

from config import get_settings
from db.base import async_session_factory
from db.models import CatalogOpportunity
from db.repositories.opportunity_catalog import OpportunityCatalogRepository
from db.repositories.users import EventRepository, MatchRepository, UserRepository
from llm.client import LLMClient
from llm.classification_utils import expand_classification_items
from llm.json_utils import coerce_llm_dict
from llm.spam_filter import is_invalid_opportunity_extraction, is_likely_spam_or_ad
from services.interest_matcher import (
    CATEGORY_DISPLAY,
    categories_to_json,
    entry_all_tags,
    extract_categories_from_text,
    rank_for_user,
    relevance_score,
    resolve_catalog_filter,
    resolve_catalog_types,
    user_matches_type,
)
from services.interest_profile import parse_format_preferences
from services.message_freshness import is_raw_message_too_old_for_llm
from services.match_digest import get_digest_buffer
from services.notification_service import NotificationService, digest_cooldown_active
from services.training_collector import (
    record_classify,
    record_match,
)

logger = logging.getLogger(__name__)


def catalog_repo(session, *, settings=None) -> OpportunityCatalogRepository:
    settings = settings or get_settings()
    return OpportunityCatalogRepository(
        session,
        no_deadline_max_age_days=settings.catalog_no_deadline_max_age_days,
    )


class OpportunityCatalogService:
    def __init__(self, notification_service: NotificationService | None = None):
        self.llm = LLMClient()
        self.notification_service = notification_service or NotificationService()
        self.settings = get_settings()

    async def classify_pending(self, limit: int | None = None) -> list[int]:
        """Фоновая классификация — только в LLM-цикле, не при онбординге."""
        if not self.llm.settings.llm_configured:
            return []

        batch_limit = limit if limit is not None else self.settings.llm_classify_batch_limit
        new_ids: list[int] = []
        async with async_session_factory() as session:
            from services.backfill_posted_at import backfill_posted_at

            await backfill_posted_at(limit=30)
            repo = catalog_repo(session)
            archived = await repo.archive_stale_unclassified(limit=200)
            await repo.deactivate_expired()
            await repo.deactivate_stale_without_deadline()
            await repo.deactivate_old_posts()
            await repo.deactivate_invalid_active()
            await repo.reclassify_active_types()
            await repo.deactivate_duplicates()
            await session.commit()
            if archived:
                logger.info("Archived %d stale unclassified posts (skipped LLM)", archived)
            pending = await repo.get_unclassified_messages(limit=batch_limit)

        for raw_message, channel in pending:
            if is_raw_message_too_old_for_llm(raw_message):
                async with async_session_factory() as session:
                    repo = catalog_repo(session)
                    await repo.create(raw_message, channel, {"is_opportunity": False})
                    await session.commit()
                continue
            try:
                is_spam, spam_reason = is_likely_spam_or_ad(raw_message.text)
                if is_spam:
                    async with async_session_factory() as session:
                        repo = catalog_repo(session)
                        await repo.create(raw_message, channel, {"is_opportunity": False})
                        await session.commit()
                    await record_classify(
                        raw_message,
                        channel,
                        llm_output=None,
                        final_output={"is_opportunity": False},
                        source="spam_filter",
                        extra_meta={"spam_reason": spam_reason},
                    )
                    continue

                data, _ = await self.llm.classify_opportunity(raw_message.text)
                data = coerce_llm_dict(data)
                if not data:
                    logger.warning("Catalog: LLM вернул не объект для message %s", raw_message.id)
                    continue

                invalid, inv_reason = is_invalid_opportunity_extraction(data, raw_message.text)
                if invalid:
                    logger.info(
                        "Catalog: skip message %s (%s)",
                        raw_message.id,
                        inv_reason,
                    )
                    async with async_session_factory() as session:
                        repo = catalog_repo(session)
                        await repo.create(raw_message, channel, {"is_opportunity": False})
                        await session.commit()
                    await record_classify(
                        raw_message,
                        channel,
                        llm_output=data,
                        final_output={"is_opportunity": False},
                        source="post_validation",
                        model_name=self.settings.llm_model_name,
                        extra_meta={"invalid_reason": inv_reason},
                    )
                    continue

                items = expand_classification_items(data)
                created_entries = []
                async with async_session_factory() as session:
                    repo = catalog_repo(session)
                    for item in items:
                        entry = await repo.create(raw_message, channel, item)
                        created_entries.append(entry)
                    await session.commit()

                finals = [
                    {
                        "is_opportunity": entry.is_active,
                        "title": entry.title,
                        "type": entry.opportunity_type,
                        "deadline": entry.deadline,
                        "description": entry.description,
                        "requirements": entry.requirements,
                        "application_url": entry.application_url,
                    }
                    for entry in created_entries
                ]
                primary = created_entries[0] if created_entries else None
                await record_classify(
                    raw_message,
                    channel,
                    llm_output=data,
                    final_output={
                        "items": finals,
                        "count": len(finals),
                        "is_opportunity": any(f["is_opportunity"] for f in finals),
                    },
                    source="llm",
                    model_name=self.settings.llm_model_name,
                    catalog_id=primary.id if primary else None,
                    extra_meta={"split_count": len(finals)},
                )
                active_ids = [entry.id for entry in created_entries if entry.is_active]
                for entry in created_entries:
                    if entry.is_active:
                        new_ids.append(entry.id)
                if active_ids:
                    from services.startify_catalog_push import schedule_catalog_push

                    schedule_catalog_push(active_ids)
                if any(e.is_active for e in created_entries):
                    logger.info(
                        "Catalog: classified message %s into %d item(s)",
                        raw_message.id,
                        sum(1 for e in created_entries if e.is_active),
                    )
            except Exception as exc:
                logger.warning("Catalog: ошибка message %s — %s", raw_message.id, exc)
                continue

        return new_ids

    async def save_user_categories_local(self, user_id: int, interest_query: str) -> list[str]:
        from services.interest_categorizer import get_or_categorize_user_interest

        async with async_session_factory() as session:
            user = await UserRepository(session).get_by_id(user_id)

        profile, categories, source = await get_or_categorize_user_interest(
            user_id,
            interest_query,
            stored_query=user.interest_query if user else None,
            stored_categories_json=user.interest_categories_json if user else None,
        )

        if user and (
            not user.interest_categories_json
            or user.interest_query != interest_query.strip()
            or source != "cached"
        ):
            async with async_session_factory() as session:
                u = await UserRepository(session).get_by_id(user_id)
                if u:
                    u.interest_categories_json = categories_to_json(categories)
                    u.interest_preferences_json = profile.preferences_json()
                    await session.commit()

        return categories

    async def instant_match_for_user(
        self,
        user_id: int,
        telegram_id: int,
        interest_query: str,
        *,
        max_cards: int | None = None,
        min_score: float | None = None,
        force: bool = False,
    ) -> tuple[int, list[str]]:
        """
        Подбор из каталога: keyword score + опциональный LLM rerank.
        Одно сообщение-подборка, не больше notification_digest_max_flush карточек.
        """
        settings = self.settings
        cap = max_cards if max_cards is not None else settings.notification_digest_max_flush
        score_floor = min_score if min_score is not None else settings.catalog_notify_min_score

        if not force and await digest_cooldown_active(user_id):
            logger.debug("instant_match skipped: digest cooldown user=%s", user_id)
            return 0, await self.save_user_categories_local(user_id, interest_query)

        categories = await self.save_user_categories_local(user_id, interest_query)

        async with async_session_factory() as session:
            repo = catalog_repo(session)
            user = await UserRepository(session).get_by_id(user_id)
            format_prefs = parse_format_preferences(user.interest_preferences_json if user else None)
            search_types, extra_tags = resolve_catalog_filter(categories)
            items = await repo.get_active_for_user(
                user_id, search_types, limit=80, extra_tags=extra_tags
            )

        candidates: list[CatalogOpportunity] = []
        for item in items:
            if not await self._already_sent(user_id, item):
                candidates.append(item)

        ranked = rank_for_user(
            interest_query,
            candidates,
            limit=cap * 3,
            min_score=score_floor,
            format_preferences=format_prefs,
        )
        if ranked and self.settings.llm_catalog_match_rerank and self.settings.llm_configured:
            from services.catalog_rerank import llm_rerank_catalog

            ranked = await llm_rerank_catalog(
                interest_query,
                ranked,
                max_pick=cap,
            )
        else:
            ranked = ranked[:cap]
        if not ranked:
            return 0, categories

        sent = 0
        for item in ranked:
            score = relevance_score(interest_query, item, format_preferences=format_prefs)
            if await self._deliver_card(
                user_id,
                telegram_id,
                item,
                flush_remaining=False,
                auto_flush=False,
            ):
                sent += 1
                await record_match(
                    user_id=user_id,
                    interest_query=interest_query,
                    entry=item,
                    relevant=True,
                    score=score,
                    source="instant_match",
                    categories=categories,
                )
        if sent:
            flushed = await self.notification_service.flush_user_digest(
                user_id,
                flush_remaining=True,
                max_items=cap,
            )
            if flushed == 0:
                await self._disable_notifications(user_id)
            return flushed, categories
        return 0, categories

    async def send_scheduled_digest(
        self,
        user_id: int,
        telegram_id: int,
        interest_query: str,
    ) -> int:
        """Утренняя подборка: сначала накопленное, иначе топ по интересам — одним сообщением."""
        cap = self.settings.notification_digest_max_flush
        if get_digest_buffer().pending_count(user_id) > 0:
            return await self.notification_service.flush_user_digest(
                user_id,
                flush_remaining=True,
                max_items=cap,
            )
        return (
            await self.instant_match_for_user(
                user_id,
                telegram_id,
                interest_query,
                max_cards=cap,
                force=False,
            )
        )[0]

    async def notify_users_for_catalog_item(self, catalog_id: int) -> set[int]:
        """Новая запись в каталоге — только пользователям, у кого есть доступ к каналу."""
        async with async_session_factory() as session:
            repo = catalog_repo(session)
            pair = await repo.get_entry_with_channel(catalog_id)
            if not pair:
                return set()
            entry, channel = pair
            if not entry.is_active:
                return set()
            from services.catalog_freshness import is_catalog_entry_fresh

            if not is_catalog_entry_fresh(entry):
                return set()
            user_repo = UserRepository(session)
            users = await user_repo.get_notification_recipients(
                channel.channel_identifier,
                is_seed=channel.is_seed,
            )

        enqueued: set[int] = set()
        for user in users:
            if not user.notifications_enabled:
                continue
            if await digest_cooldown_active(user.id):
                continue
            if not user_matches_type(
                user.interest_query or "",
                user.interest_categories_json,
                entry.opportunity_type,
            ):
                continue
            if await self._already_sent(user.id, entry):
                continue
            min_score = self.settings.catalog_notify_min_score
            if relevance_score(user.interest_query or "", entry) < min_score:
                score = relevance_score(user.interest_query or "", entry)
                async with async_session_factory() as session:
                    match_repo = MatchRepository(session)
                    await match_repo.mark_processed(
                        user.id,
                        entry.raw_message_id,
                        False,
                        json.dumps({"source": "catalog_notify", "score": score}, ensure_ascii=False),
                    )
                    await session.commit()
                await record_match(
                    user_id=user.id,
                    interest_query=user.interest_query or "",
                    entry=entry,
                    relevant=False,
                    score=score,
                    source="catalog_notify",
                )
                continue
            if await self._deliver_card(
                user.id,
                user.telegram_id,
                entry,
                auto_flush=False,
            ):
                enqueued.add(user.id)
                await record_match(
                    user_id=user.id,
                    interest_query=user.interest_query or "",
                    entry=entry,
                    relevant=True,
                    score=relevance_score(user.interest_query or "", entry),
                    source="catalog_notify",
                )
        return enqueued

    async def flush_pending_digests(self, user_ids: set[int]) -> int:
        """Отправить накопленные карточки одной подборкой (до notification_digest_max_flush)."""
        if not user_ids:
            return 0
        cap = self.settings.notification_digest_max_flush
        sent = 0
        for user_id in user_ids:
            if await digest_cooldown_active(user_id):
                continue
            sent += await self.notification_service.flush_user_digest(
                user_id,
                flush_remaining=True,
                max_items=cap,
            )
        return sent

    async def _disable_notifications(self, user_id: int) -> None:
        async with async_session_factory() as session:
            await UserRepository(session).set_notifications_enabled(user_id, False)
            await session.commit()

    async def _already_sent(self, user_id: int, entry: CatalogOpportunity) -> bool:
        async with async_session_factory() as session:
            match_repo = MatchRepository(session)
            if await match_repo.is_done(user_id, entry.raw_message_id):
                return True
            if await match_repo.was_sent_for_link(user_id, entry.message_link):
                return True
        return False

    async def _deliver_card(
        self,
        user_id: int,
        telegram_id: int,
        entry: CatalogOpportunity,
        *,
        flush_remaining: bool = False,
        auto_flush: bool = False,
    ) -> bool:
        tag_labels = []
        for tag in entry_all_tags(entry):
            if tag in CATEGORY_DISPLAY:
                tag_labels.append(CATEGORY_DISPLAY[tag][1])
            else:
                tag_labels.append(tag.capitalize())
        card_data = {
            "title": entry.title,
            "type": entry.opportunity_type,
            "tags": tag_labels,
            "deadline": entry.deadline,
            "description": entry.description,
            "requirements": entry.requirements,
            "source_channel_name": entry.source_channel_name,
            "message_link": entry.message_link,
            "application_url": entry.application_url,
        }
        async with async_session_factory() as session:
            match_repo = MatchRepository(session)
            event_repo = EventRepository(session)
            if await match_repo.was_sent_for_link(user_id, entry.message_link):
                return False
            try:
                await match_repo.mark_processed(
                    user_id,
                    entry.raw_message_id,
                    True,
                    json.dumps({"source": "catalog", "catalog_id": entry.id}, ensure_ascii=False),
                )
                sent = await match_repo.create_sent_match(user_id, entry.raw_message_id, card_data)
                await event_repo.log("card_sent", user_id=user_id, related_id=sent.id)
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return False

        ok = await self.notification_service.enqueue_match(
            user_id,
            telegram_id,
            sent.id,
            card_data,
            flush_remaining=flush_remaining,
            auto_flush=auto_flush,
        )
        if not ok:
            await self._disable_notifications(user_id)
            return False
        return True

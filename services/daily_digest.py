"""Ежедневная подборка: новые совпадения или «пока пусто» с рекомендациями."""

import logging
from datetime import datetime, timezone

from analytics.event_types import CARD_SENT, DAILY_DIGEST_EMPTY, DAILY_DIGEST_MATCH
from bot.instance import get_notify_bot
from bot.keyboards import interest_browse_keyboard
from bot.texts import get_daily_empty_digest_message
from db.base import async_session_factory
from db.models import CatalogOpportunity, User
from db.repositories.opportunity_catalog import parse_interest_categories
from db.repositories.users import EventRepository, SystemStateRepository, UserRepository
from logging_setup import log_error
from services.interest_matcher import rank_for_user, relevance_score, resolve_catalog_filter
from services.notification_service import NotificationService, is_unreachable_user_error
from services.opportunity_catalog import OpportunityCatalogService, catalog_repo

logger = logging.getLogger(__name__)


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _daily_digest_state_key(user_id: int) -> str:
    return f"daily_digest:{user_id}"


async def _already_ran_today(user_id: int) -> bool:
    async with async_session_factory() as session:
        state_repo = SystemStateRepository(session)
        last = await state_repo.get(_daily_digest_state_key(user_id))
    return last == _today_utc()


async def _mark_ran_today(user_id: int) -> None:
    async with async_session_factory() as session:
        await SystemStateRepository(session).set(_daily_digest_state_key(user_id), _today_utc())
        await session.commit()


async def _cards_sent_since(user_id: int, since: datetime) -> int:
    async with async_session_factory() as session:
        return await EventRepository(session).count_user_events_since(user_id, CARD_SENT, since)


async def _get_recommendations(
    catalog_service: OpportunityCatalogService,
    user: User,
    *,
    limit: int = 3,
) -> list[CatalogOpportunity]:
    interest_query = (user.interest_query or "").strip()
    if not interest_query:
        return []

    categories = []
    if user.interest_categories_json:
        try:
            import json

            data = json.loads(user.interest_categories_json)
            if isinstance(data, list):
                categories = [str(x) for x in data]
        except (json.JSONDecodeError, TypeError):
            pass

    async with async_session_factory() as session:
        repo = catalog_repo(session)
        search_types, extra_tags = resolve_catalog_filter(categories)
        items = await repo.get_active_for_user(
            user.id,
            search_types,
            limit=60,
            extra_tags=extra_tags,
        )

    candidates: list[CatalogOpportunity] = []
    for item in items:
        if not await catalog_service._already_sent(user.id, item):
            candidates.append(item)

    ranked = rank_for_user(interest_query, candidates, limit=limit, min_score=1.0)
    if len(ranked) >= limit:
        return ranked

    seen = {item.id for item in ranked}
    scored = sorted(
        ((relevance_score(interest_query, item), item) for item in candidates if item.id not in seen),
        key=lambda pair: pair[0],
        reverse=True,
    )
    for _, item in scored:
        ranked.append(item)
        if len(ranked) >= limit:
            break
    return ranked


async def _send_empty_digest(
    user: User,
    recommendations: list[CatalogOpportunity],
    category_counts: dict[str, int] | None,
) -> bool:
    text = get_daily_empty_digest_message(recommendations, category_counts=category_counts)
    profile_categories = parse_interest_categories(user.interest_categories_json)
    reply_markup = interest_browse_keyboard(profile_categories, category_counts or {})
    bot = get_notify_bot()
    try:
        await bot.send_message(
            user.telegram_id,
            text,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )
        return True
    except Exception as exc:
        if is_unreachable_user_error(exc):
            logger.info("Daily digest: user %s недоступен — %s", user.telegram_id, exc)
            return False
        raise


async def run_daily_digest_for_user(
    user: User,
    catalog_service: OpportunityCatalogService,
    *,
    force: bool = False,
) -> str:
    """
    Вернёт: skipped | matched | empty | unreachable
    """
    if not user.notifications_enabled:
        return "skipped"
    interest_query = (user.interest_query or "").strip()
    if not interest_query:
        return "skipped"
    if not force and await _already_ran_today(user.id):
        return "skipped"

    since_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    if await _cards_sent_since(user.id, since_day) > 0:
        await _mark_ran_today(user.id)
        return "skipped"

    try:
        sent = await catalog_service.send_scheduled_digest(
            user.id,
            user.telegram_id,
            interest_query,
        )

        if sent > 0:
            async with async_session_factory() as session:
                await EventRepository(session).log(
                    DAILY_DIGEST_MATCH,
                    user_id=user.id,
                    metadata={"sent": sent},
                )
                await session.commit()
            await _mark_ran_today(user.id)
            return "matched"

        if await _cards_sent_since(user.id, since_day) > 0:
            await _mark_ran_today(user.id)
            return "skipped"

        recommendations = await _get_recommendations(catalog_service, user, limit=3)
        category_counts = None
        if not recommendations:
            async with async_session_factory() as session:
                category_counts = await catalog_repo(session).count_active_by_type_for_user(user.id)

        ok = await _send_empty_digest(user, recommendations, category_counts)
        if not ok:
            async with async_session_factory() as session:
                await UserRepository(session).set_notifications_enabled(user.id, False)
                await session.commit()
            return "unreachable"

        async with async_session_factory() as session:
            await EventRepository(session).log(
                DAILY_DIGEST_EMPTY,
                user_id=user.id,
                metadata={"recommendations": len(recommendations)},
            )
            await session.commit()
        await _mark_ran_today(user.id)
        return "empty"
    except Exception as exc:
        log_error(logger, "daily_digest_user", exc, {"user_id": user.id})
        return "error"


async def run_daily_digests_for_all_users(
    notification_service: NotificationService | None = None,
) -> dict[str, int]:
    """Запускается после суточного скана каналов."""
    service = notification_service or NotificationService()
    catalog_service = OpportunityCatalogService(service)

    async with async_session_factory() as session:
        users = [
            u
            for u in await UserRepository(session).list_with_interests()
            if u.notifications_enabled
        ]

    stats = {"matched": 0, "empty": 0, "skipped": 0, "unreachable": 0, "error": 0}
    logger.info("Daily digest: %d users with interests", len(users))

    for user in users:
        result = await run_daily_digest_for_user(user, catalog_service)
        stats[result] = stats.get(result, 0) + 1

    logger.info(
        "Daily digest done: matched=%d empty=%d skipped=%d unreachable=%d error=%d",
        stats.get("matched", 0),
        stats.get("empty", 0),
        stats.get("skipped", 0),
        stats.get("unreachable", 0),
        stats.get("error", 0),
    )
    return stats

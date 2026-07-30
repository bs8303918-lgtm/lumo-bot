"""Еженедельный проактивный дайджест: топ-5 подборок под профиль, без захода в приложение."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from bot.instance import get_notify_bot
from db.base import async_session_factory
from db.models import CatalogOpportunity, User
from db.repositories.users import SystemStateRepository, UserRepository
from logging_setup import log_error
from services.match_score import compute_match_score, raw_match_score
from services.notification_service import NotificationService, is_unreachable_user_error
from services.opportunity_catalog import OpportunityCatalogService, catalog_repo

logger = logging.getLogger(__name__)

TOP_N = 5
MIN_RAW_SCORE = 3.0


def _iso_week(now: datetime) -> str:
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def _state_key(user_id: int) -> str:
    return f"weekly_digest:{user_id}"


async def _already_sent_this_week(user_id: int) -> bool:
    async with async_session_factory() as session:
        raw = await SystemStateRepository(session).get(_state_key(user_id))
    return raw == _iso_week(datetime.now(timezone.utc))


async def _mark_sent_this_week(user_id: int) -> None:
    async with async_session_factory() as session:
        await SystemStateRepository(session).set(_state_key(user_id), _iso_week(datetime.now(timezone.utc)))
        await session.commit()


async def _top_matches(
    catalog_service: OpportunityCatalogService, user: User
) -> list[tuple[CatalogOpportunity, int]]:
    async with async_session_factory() as session:
        repo = catalog_repo(session)
        items = await repo.list_all_active_for_user(user.id, [], max_rows=150)

    candidates = [item for item in items if not await catalog_service._already_sent(user.id, item)]
    scored = sorted(
        ((raw_match_score(user, item), item) for item in candidates),
        key=lambda pair: pair[0],
        reverse=True,
    )
    top = [(item, compute_match_score(user, item)) for score, item in scored if score >= MIN_RAW_SCORE][:TOP_N]
    return top


def _format_weekly_digest(matches: list[tuple[CatalogOpportunity, int]]) -> str:
    lines = ["🗓 Твоя подборка недели — топ-5 под твой профиль:\n"]
    for idx, (entry, score) in enumerate(matches, start=1):
        lines.append(
            f"{idx}. {entry.title}\n"
            f"   🎯 Совпадение: {score}% · 📅 Дедлайн: {entry.deadline}\n"
            f"   🔗 {entry.message_link}"
        )
    lines.append("\nОткрой Lumo, чтобы посмотреть все детали и сохранить понравившиеся.")
    return "\n".join(lines)


async def run_weekly_digest_for_user(user: User, catalog_service: OpportunityCatalogService) -> str:
    """Вернёт: skipped | sent | empty | unreachable"""
    if not user.notifications_enabled:
        return "skipped"
    if await _already_sent_this_week(user.id):
        return "skipped"

    matches = await _top_matches(catalog_service, user)
    if not matches:
        return "empty"

    bot = get_notify_bot()
    try:
        await bot.send_message(
            user.telegram_id,
            _format_weekly_digest(matches),
            disable_web_page_preview=True,
        )
    except Exception as exc:
        if is_unreachable_user_error(exc):
            return "unreachable"
        raise

    await _mark_sent_this_week(user.id)
    return "sent"


async def run_weekly_digest_cycle() -> dict[str, int]:
    service = NotificationService()
    catalog_service = OpportunityCatalogService(service)

    async with async_session_factory() as session:
        users = [u for u in await UserRepository(session).list_with_interests() if u.notifications_enabled]

    stats = {"sent": 0, "empty": 0, "skipped": 0, "unreachable": 0, "error": 0}
    for user in users:
        try:
            result = await run_weekly_digest_for_user(user, catalog_service)
        except Exception as exc:
            log_error(logger, "weekly_digest_user", exc, {"user_id": user.id})
            result = "error"
        stats[result] = stats.get(result, 0) + 1
    return stats


async def run_weekly_digest_forever(interval_seconds: int | None = None) -> None:
    from config import get_settings

    interval = interval_seconds or get_settings().weekly_digest_check_interval_seconds
    while True:
        try:
            stats = await run_weekly_digest_cycle()
            if stats.get("sent"):
                logger.info("Weekly digest: %s", stats)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_error(logger, "weekly_digest", exc)
        await asyncio.sleep(interval)

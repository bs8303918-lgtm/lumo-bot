"""Напоминания о дедлайне сохранённых конкурсов: за неделю, за 3 дня, за день — в Telegram."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone

from bot.instance import get_notify_bot
from db.base import async_session_factory
from db.models import SavedOpportunity
from llm.deadline import parse_deadline
from logging_setup import log_error
from services.catalog_freshness import message_posted_at
from services.notification_service import is_unreachable_user_error

logger = logging.getLogger(__name__)

REMINDER_WINDOWS: dict[int, str] = {7: "7d", 3: "3d", 1: "1d"}
_WINDOW_LABEL = {"7d": "через неделю", "3d": "через 3 дня", "1d": "завтра"}


def _days_left(row: SavedOpportunity, *, today: date) -> int | None:
    entry = row.catalog
    if entry is None:
        return None
    anchor = None
    posted = message_posted_at(entry)
    if posted:
        anchor = posted.date()
    parsed = parse_deadline(entry.deadline, anchor_date=anchor)
    if parsed is None:
        return None
    return (parsed - today).days


async def _already_sent(session, user_id: int, catalog_id: int, window: str) -> bool:
    from db.repositories.deadline_reminder_log import DeadlineReminderLogRepository

    return await DeadlineReminderLogRepository(session).exists(user_id, catalog_id, window)


async def _mark_sent(session, user_id: int, catalog_id: int, window: str) -> None:
    from db.repositories.deadline_reminder_log import DeadlineReminderLogRepository

    await DeadlineReminderLogRepository(session).mark_sent(user_id, catalog_id, window)


def _format_reminder(row: SavedOpportunity, window: str) -> str:
    entry = row.catalog
    label = _WINDOW_LABEL.get(window, window)
    return (
        f"⏰ Дедлайн {label}!\n\n"
        f"📌 {entry.title}\n"
        f"📅 Дедлайн: {entry.deadline}\n"
        f"🗂 Статус: {row.status}\n\n"
        f"🔗 {entry.message_link}"
    )


async def run_deadline_reminder_cycle() -> dict[str, int]:
    from db.repositories.saved_opportunities import SavedOpportunityRepository

    stats = {"sent": 0, "skipped": 0, "unreachable": 0}
    today = datetime.now(timezone.utc).date()
    bot = get_notify_bot()

    async with async_session_factory() as session:
        rows = await SavedOpportunityRepository(session).list_active_for_reminders()

        for row in rows:
            if row.user is None or row.catalog is None:
                continue
            if not row.user.notifications_enabled:
                continue
            days_left = _days_left(row, today=today)
            if days_left is None or days_left not in REMINDER_WINDOWS:
                continue
            window = REMINDER_WINDOWS[days_left]
            if await _already_sent(session, row.user_id, row.catalog_id, window):
                continue

            try:
                await bot.send_message(
                    row.user.telegram_id,
                    _format_reminder(row, window),
                    disable_web_page_preview=True,
                )
                await _mark_sent(session, row.user_id, row.catalog_id, window)
                await session.commit()
                stats["sent"] += 1
            except Exception as exc:
                if is_unreachable_user_error(exc):
                    stats["unreachable"] += 1
                    continue
                log_error(
                    logger,
                    "deadline_reminder",
                    exc,
                    {"user_id": row.user_id, "catalog_id": row.catalog_id, "window": window},
                )
                stats["skipped"] += 1

    return stats


async def run_deadline_reminders_forever(interval_seconds: int | None = None) -> None:
    from config import get_settings

    interval = interval_seconds or get_settings().deadline_reminder_check_interval_seconds
    while True:
        try:
            stats = await run_deadline_reminder_cycle()
            if stats.get("sent"):
                logger.info("Deadline reminders: %s", stats)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_error(logger, "deadline_reminders", exc)
        await asyncio.sleep(interval)

"""Разовая рассылка «бот был на техобслуживании»."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from analytics.event_types import MAINTENANCE_NOTICE_SENT, USER_REGISTERED
from bot.instance import get_notify_bot
from bot.keyboards import main_menu_keyboard, webapp_open_inline
from bot.texts import get_welcome_text
from db.base import async_session_factory
from db.models import Event, User
from db.repositories.users import EventRepository, UserRepository
from services.notification_service import is_unreachable_user_error

logger = logging.getLogger(__name__)

BATCH_SLUG = "maintenance_2026-06-24"

MAINTENANCE_TEXT = (
    "🛠 <b>Извини!</b> Бот был на техобслуживании — мог не ответить или работать криво.\n\n"
    "Сейчас всё снова в строю. Нажми /start или /set_interest, чтобы продолжить 🎯"
)


async def _already_sent(session, user_id: int, batch: str) -> bool:
    result = await session.execute(
        select(Event.id)
        .where(Event.user_id == user_id)
        .where(Event.event_type == MAINTENANCE_NOTICE_SENT)
        .where(Event.metadata_json.contains(batch))
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_registered_user_ids(*, days: int = 7) -> list[int]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    async with async_session_factory() as session:
        result = await session.execute(
            select(User.id)
            .join(Event, Event.user_id == User.id)
            .where(Event.event_type == USER_REGISTERED)
            .where(Event.created_at >= since)
            .distinct()
            .order_by(User.id)
        )
        return [row[0] for row in result.all()]


async def send_maintenance_apology(
    *,
    days: int = 7,
    batch: str = BATCH_SLUG,
    force: bool = False,
    resend_welcome: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    user_ids = await get_registered_user_ids(days=days)
    stats = {
        "target": len(user_ids),
        "sent": 0,
        "skipped": 0,
        "unreachable": 0,
        "error": 0,
    }

    if dry_run:
        return stats

    bot = get_notify_bot()
    inline = webapp_open_inline()

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        users = []
        for user_id in user_ids:
            user = await user_repo.get_by_id(user_id)
            if user:
                users.append(user)

    for user in users:
        async with async_session_factory() as session:
            if not force and await _already_sent(session, user.id, batch):
                stats["skipped"] += 1
                continue

        try:
            await bot.send_message(
                user.telegram_id,
                MAINTENANCE_TEXT,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(),
            )
            if resend_welcome:
                await bot.send_message(
                    user.telegram_id,
                    get_welcome_text(),
                    reply_markup=main_menu_keyboard(),
                )
            if inline:
                await bot.send_message(
                    user.telegram_id,
                    "📱 Mini App снова доступен:",
                    reply_markup=inline,
                )
        except Exception as exc:
            if is_unreachable_user_error(exc):
                stats["unreachable"] += 1
            else:
                logger.warning("maintenance send failed user=%s: %s", user.id, exc)
                stats["error"] += 1
            continue

        async with async_session_factory() as session:
            await EventRepository(session).log(
                MAINTENANCE_NOTICE_SENT,
                user_id=user.id,
                metadata={"batch": batch, "resend_welcome": resend_welcome},
            )
            await session.commit()
        stats["sent"] += 1
        await asyncio.sleep(0.05)

    return stats

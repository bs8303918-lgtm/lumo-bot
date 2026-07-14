"""Разовая рассылка: Lumo переходит на платный режим."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from analytics.event_types import PAID_MODE_NOTICE_SENT
from bot.instance import get_notify_bot
from bot.keyboards import subscription_upsell_keyboard
from db.base import async_session_factory
from db.models import Event, User
from db.repositories.users import EventRepository, UserRepository
from services.notification_service import is_unreachable_user_error

logger = logging.getLogger(__name__)

BATCH_SLUG = "paid_mode_2026-07-14"

PAID_MODE_TEXT = (
    "👋 Сәлем!\n\n"
    "Lumo переходит на платный режим — так бот станет точнее, быстрее и стабильнее.\n\n"
    "• <b>1 месяц</b> — 1 890 ₸\n"
    "• <b>3 месяца</b> — 4 990 ₸ (вкладка Price в Mini App)\n"
    "• <b>6 месяцев</b> — 5 940 ₸\n\n"
    "🎁 <b>Для своих</b> — в подарок <b>менторская поддержка</b>: поможем с подачей "
    "на конкурсы, гранты и стажировки.\n\n"
    "Плюс <b>7 дней бесплатно</b>, чтобы попробовать без оплаты.\n\n"
    "Напиши @taton4i — подключим доступ и дадим бесплатную консультацию.\n\n"
    "Спасибо, что с нами с самого начала 💙"
)


async def _already_sent(session, user_id: int, batch: str) -> bool:
    result = await session.execute(
        select(Event.id)
        .where(Event.user_id == user_id)
        .where(Event.event_type == PAID_MODE_NOTICE_SENT)
        .where(Event.metadata_json.contains(batch))
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_all_user_ids() -> list[int]:
    async with async_session_factory() as session:
        result = await session.execute(select(User.id).order_by(User.id))
        return [row[0] for row in result.all()]


async def send_paid_mode_notice(
    *,
    batch: str = BATCH_SLUG,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    user_ids = await get_all_user_ids()
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
    markup = subscription_upsell_keyboard()

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
                PAID_MODE_TEXT,
                parse_mode="HTML",
                reply_markup=markup,
            )
        except Exception as exc:
            if is_unreachable_user_error(exc):
                stats["unreachable"] += 1
            else:
                logger.warning("paid-mode send failed user=%s: %s", user.id, exc)
                stats["error"] += 1
            continue

        async with async_session_factory() as session:
            await EventRepository(session).log(
                PAID_MODE_NOTICE_SENT,
                user_id=user.id,
                metadata={"batch": batch},
            )
            await session.commit()
        stats["sent"] += 1
        await asyncio.sleep(0.05)

    return stats

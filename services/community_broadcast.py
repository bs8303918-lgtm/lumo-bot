"""Рассылка приглашения в Telegram-сообщество Lumo."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from analytics.event_types import COMMUNITY_INVITE_SENT
from bot.instance import get_notify_bot
from bot.keyboards import community_join_inline, main_menu_keyboard
from bot.texts import get_community_invite_text
from db.base import async_session_factory
from db.models import Event, User
from db.repositories.users import EventRepository
from services.notification_service import is_unreachable_user_error

logger = logging.getLogger(__name__)

BATCH_SLUG = "community_invite_2026-06-26"


async def _already_sent(session, user_id: int, batch: str) -> bool:
    result = await session.execute(
        select(Event.id)
        .where(Event.user_id == user_id)
        .where(Event.event_type == COMMUNITY_INVITE_SENT)
        .where(Event.metadata_json.contains(batch))
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_all_user_ids() -> list[int]:
    async with async_session_factory() as session:
        result = await session.execute(select(User.id).order_by(User.id))
        return [row[0] for row in result.all()]


async def user_received_community_invite(session, user_id: int) -> bool:
    return await _already_sent(session, user_id, BATCH_SLUG)


async def send_community_invite_to_user(
    user: User,
    *,
    batch: str = BATCH_SLUG,
    force: bool = False,
) -> str:
    """Returns: sent | skipped | unreachable | error | no_url"""
    inline = community_join_inline()
    if not inline:
        return "no_url"

    async with async_session_factory() as session:
        if not force and await _already_sent(session, user.id, batch):
            return "skipped"

    bot = get_notify_bot()
    text = get_community_invite_text()
    try:
        await bot.send_message(
            user.telegram_id,
            text,
            parse_mode="HTML",
            reply_markup=inline,
        )
    except Exception as exc:
        if is_unreachable_user_error(exc):
            return "unreachable"
        logger.warning("community invite failed user=%s: %s", user.id, exc)
        return "error"

    async with async_session_factory() as session:
        await EventRepository(session).log(
            COMMUNITY_INVITE_SENT,
            user_id=user.id,
            metadata={"batch": batch, "source": "single"},
        )
        await session.commit()
    return "sent"


async def get_community_invite_stats() -> dict:
    async with async_session_factory() as session:
        from sqlalchemy import func

        total_users = await session.scalar(select(func.count()).select_from(User))
        invited = await session.scalar(
            select(func.count(func.distinct(Event.user_id)))
            .where(Event.event_type == COMMUNITY_INVITE_SENT)
        )
    return {
        "totalUsers": int(total_users or 0),
        "invitedUsers": int(invited or 0),
        "batch": BATCH_SLUG,
    }


async def send_community_invite(
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
    inline = community_join_inline()
    if not inline:
        logger.error(
            "community_telegram_url invalid — set COMMUNITY_TELEGRAM_URL=https://t.me/+... in Railway"
        )
        stats["error"] = stats["target"]
        return stats

    text = get_community_invite_text()

    async with async_session_factory() as session:
        from db.repositories.users import UserRepository

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
                text,
                parse_mode="HTML",
                reply_markup=inline,
            )
        except Exception as exc:
            if is_unreachable_user_error(exc):
                stats["unreachable"] += 1
            else:
                logger.warning("community invite failed user=%s: %s", user.id, exc)
                stats["error"] += 1
            continue

        async with async_session_factory() as session:
            await EventRepository(session).log(
                COMMUNITY_INVITE_SENT,
                user_id=user.id,
                metadata={"batch": batch},
            )
            await session.commit()
        stats["sent"] += 1
        await asyncio.sleep(0.05)

    return stats

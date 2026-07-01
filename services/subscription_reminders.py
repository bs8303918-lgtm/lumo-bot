"""Push-напоминания по trial / истечению тарифа (Duolingo-style upsell)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from bot.keyboards import subscription_upsell_keyboard
from bot.instance import get_notify_bot
from bot.texts.subscription_push import (
    get_trial_expired_message,
    get_trial_remind_1d,
    get_trial_remind_3d,
    get_trial_winback_3d,
    get_trial_winback_7d,
)
from db.base import async_session_factory
from db.models import User
from db.repositories.users import EventRepository, SystemStateRepository
from logging_setup import log_error
from services.notification_service import is_unreachable_user_error
from services.subscription import (
    PLAN_TRIAL_7D,
    is_paid_plan_active,
)

logger = logging.getLogger(__name__)

REMINDER_SPECS: tuple[tuple[str, timedelta, timedelta, str], ...] = (
    # expires + low <= now <= expires + high
    ("remind_3d", timedelta(days=-3, hours=-12), timedelta(days=-2, hours=-12), "subscription_remind_3d"),
    ("remind_1d", timedelta(hours=-36), timedelta(hours=-12), "subscription_remind_1d"),
    ("expired", timedelta(hours=0), timedelta(hours=6), "subscription_trial_expired"),
    ("winback_3d", timedelta(days=2, hours=12), timedelta(days=3, hours=12), "subscription_winback_3d"),
    ("winback_7d", timedelta(days=6, hours=12), timedelta(days=7, hours=12), "subscription_winback_7d"),
)


def _push_key(user_id: int, kind: str) -> str:
    return f"sub_push:{user_id}:{kind}"


def _expires_aware(user: User) -> datetime | None:
    exp = user.tariff_expires_at
    if exp is None:
        return None
    if exp.tzinfo is None:
        return exp.replace(tzinfo=timezone.utc)
    return exp


def _message_for_kind(kind: str, expires_at: datetime | None) -> str:
    if kind == "remind_3d":
        return get_trial_remind_3d(expires_at)
    if kind == "remind_1d":
        return get_trial_remind_1d(expires_at)
    if kind == "expired":
        return get_trial_expired_message()
    if kind == "winback_3d":
        return get_trial_winback_3d()
    if kind == "winback_7d":
        return get_trial_winback_7d()
    return ""


def _in_window(now: datetime, expires: datetime, low: timedelta, high: timedelta) -> bool:
    """low/high — смещения от expires: expires + low <= now <= expires + high."""
    start = expires + low
    end = expires + high
    return start <= now <= end


async def _should_send(user: User, kind: str, now: datetime, state_repo: SystemStateRepository) -> bool:
    if not user.notifications_enabled:
        return False

    plan = (user.tariff_plan or "").lower()
    expires = _expires_aware(user)

    if kind in ("remind_3d", "remind_1d"):
        if plan != PLAN_TRIAL_7D or expires is None:
            return False
        if not is_paid_plan_active(user, now=now):
            return False
        for spec_kind, low, high, _ in REMINDER_SPECS:
            if spec_kind == kind:
                return _in_window(now, expires, low, high)
        return False

    if kind == "expired":
        if plan != PLAN_TRIAL_7D or expires is None:
            return False
        if expires > now:
            return False
        if is_paid_plan_active(user, now=now):
            return False
        for spec_kind, low, high, _ in REMINDER_SPECS:
            if spec_kind == kind:
                return _in_window(now, expires, low, high)
        return False

    if kind in ("winback_3d", "winback_7d"):
        if expires is None:
            return False
        if is_paid_plan_active(user, now=now):
            return False
        if plan not in (PLAN_TRIAL_7D, "freemium"):
            return False
        if expires > now:
            return False
        for spec_kind, low, high, _ in REMINDER_SPECS:
            if spec_kind == kind:
                return _in_window(now, expires, low, high)
        return False

    return False


async def _send_push(user: User, kind: str, event_type: str) -> bool:
    text = _message_for_kind(kind, _expires_aware(user))
    if not text:
        return False
    keyboard = subscription_upsell_keyboard()
    bot = get_notify_bot()
    try:
        await bot.send_message(
            user.telegram_id,
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard,
        )
    except Exception as exc:
        if is_unreachable_user_error(exc):
            logger.info("Subscription push skipped — user %s unreachable", user.telegram_id)
            async with async_session_factory() as session:
                from db.repositories.users import UserRepository

                await UserRepository(session).set_notifications_enabled(user.id, False)
                await session.commit()
            return False
        raise
    return True


async def run_subscription_reminder_cycle() -> dict[str, int]:
    now = datetime.now(timezone.utc)
    stats = {kind: 0 for kind, *_ in REMINDER_SPECS}
    stats["skipped"] = 0

    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.tariff_expires_at.is_not(None))
        )
        users = list(result.scalars().all())
        result2 = await session.execute(
            select(User).where(
                User.tariff_plan == PLAN_TRIAL_7D,
                User.tariff_expires_at.is_(None),
            )
        )
        users.extend(result2.scalars().all())

    seen_ids: set[int] = set()
    unique_users: list[User] = []
    for user in users:
        if user.id in seen_ids:
            continue
        seen_ids.add(user.id)
        unique_users.append(user)

    for user in unique_users:
        async with async_session_factory() as session:
            state_repo = SystemStateRepository(session)
            event_repo = EventRepository(session)
            for kind, _, _, event_type in REMINDER_SPECS:
                if await state_repo.get(_push_key(user.id, kind)):
                    continue
                if not await _should_send(user, kind, now, state_repo):
                    continue
                try:
                    sent = await _send_push(user, kind, event_type)
                except Exception as exc:
                    log_error(logger, "subscription_reminder", exc, {"user_id": user.id, "kind": kind})
                    stats["skipped"] += 1
                    continue
                if not sent:
                    stats["skipped"] += 1
                    continue
                await state_repo.set(_push_key(user.id, kind), now.isoformat())
                await event_repo.log(
                    event_type,
                    user_id=user.id,
                    metadata={"kind": kind, "plan": user.tariff_plan},
                )
                await session.commit()
                stats[kind] += 1
                logger.info("Subscription push %s → user %s", kind, user.telegram_id)

    return stats


async def run_subscription_reminders_forever(interval_seconds: int | None = None) -> None:
    from config import get_settings

    interval = interval_seconds or get_settings().subscription_reminder_interval_seconds
    while True:
        try:
            stats = await run_subscription_reminder_cycle()
            sent_total = sum(v for k, v in stats.items() if k not in ("skipped",))
            if sent_total:
                logger.info("Subscription reminders: %s", stats)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_error(logger, "subscription_reminders", exc)
        await asyncio.sleep(interval)

"""Ручная выдача тарифа (пока оплата через @taton4i)."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import SystemState, User
from db.repositories.users import EventRepository
from services.subscription import (
    PLAN_TRIAL_7D,
    expires_at_for_plan,
    normalize_plan_id,
)

PUSH_KINDS = (
    "trial_day2",
    "trial_halftime",
    "remind_3d",
    "remind_1d",
    "expired",
    "winback_3d",
    "winback_7d",
    "winback_14d",
)


async def clear_subscription_push_flags(session: AsyncSession, user_id: int) -> None:
    for kind in PUSH_KINDS:
        await session.execute(
            delete(SystemState).where(SystemState.key == f"sub_push:{user_id}:{kind}")
        )


async def grant_trial(session: AsyncSession, user: User, *, days: int = 7) -> User:
    user.tariff_plan = PLAN_TRIAL_7D
    user.tariff_expires_at = expires_at_for_plan(PLAN_TRIAL_7D)
    await clear_subscription_push_flags(session, user.id)
    await EventRepository(session).log(
        "subscription_trial_granted",
        user_id=user.id,
        metadata={"source": "admin_grant", "days": days},
    )
    await session.flush()
    return user


async def grant_plan(session: AsyncSession, user: User, plan_id: str) -> User:
    plan = normalize_plan_id(plan_id) or plan_id.lower().strip()
    user.tariff_plan = plan
    user.tariff_expires_at = expires_at_for_plan(plan)
    await clear_subscription_push_flags(session, user.id)
    await EventRepository(session).log(
        "subscription_activated",
        user_id=user.id,
        metadata={"source": "admin_grant", "plan": plan},
    )
    await session.flush()
    return user

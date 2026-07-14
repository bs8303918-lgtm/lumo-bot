"""Startify deep link → пробный тариф 7 дней."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User
from db.repositories.users import EventRepository, SystemStateRepository
from services.subscription import (
    DEEP_LINK_PREFIX,
    PAID_PLANS,
    PLAN_FREEMIUM,
    PLAN_TRIAL_7D,
    PLAN_UNLIMITED,
    expires_at_for_plan,
    is_paid_plan_active,
    normalize_plan_id,
    parse_startify_payload,
)

_TRIAL_USED_KEY = "startify_trial_used:{user_id}"


@dataclass
class StartifyStartResult:
    attributed: bool = False
    trial_granted: bool = False
    partner_ref: str | None = None


def _trial_used_key(user_id: int) -> str:
    return _TRIAL_USED_KEY.format(user_id=user_id)


async def apply_startify_start(
    session: AsyncSession,
    user: User,
    payload: str | None,
) -> StartifyStartResult:
    """
    Deep link sf_* от AI Startify:
    - сохраняем partner_source / partner_ref
    - выдаём trial_7d один раз (или снова, если в ссылке явно trial_7d)
    """
    result = StartifyStartResult()
    if not payload or not payload.strip().lower().startswith(DEEP_LINK_PREFIX):
        return result

    ref, pending = parse_startify_payload(payload.strip())
    user.partner_source = "startify"
    if ref:
        user.partner_ref = ref
        result.partner_ref = ref
    result.attributed = True

    pending_norm = normalize_plan_id(pending) if pending else None
    if pending_norm in PAID_PLANS and pending_norm != PLAN_TRIAL_7D:
        await session.flush()
        return result

    if is_paid_plan_active(user) and (user.tariff_plan or "").lower() not in (PLAN_FREEMIUM, PLAN_TRIAL_7D):
        await session.flush()
        return result

    if user.tariff_plan == PLAN_UNLIMITED:
        await session.flush()
        return result

    state_repo = SystemStateRepository(session)
    trial_used = (await state_repo.get(_trial_used_key(user.id), "0")) == "1"
    explicit_trial = pending_norm == PLAN_TRIAL_7D or pending_norm is None

    if trial_used and not explicit_trial:
        await session.flush()
        return result

    if user.tariff_plan == PLAN_TRIAL_7D and is_paid_plan_active(user):
        await session.flush()
        return result

    user.tariff_plan = PLAN_TRIAL_7D
    user.tariff_expires_at = expires_at_for_plan(PLAN_TRIAL_7D)
    await state_repo.set(_trial_used_key(user.id), "1")
    from services.subscription_grant import clear_subscription_push_flags

    await clear_subscription_push_flags(session, user.id)
    for push_key in ("remind_3d", "remind_1d", "expired", "winback_3d", "winback_7d"):
        await state_repo.set(f"sub_push:{user.id}:{push_key}", "")

    await EventRepository(session).log(
        "subscription_trial_granted",
        user_id=user.id,
        metadata={"partnerRef": ref, "pendingPlan": pending_norm or PLAN_TRIAL_7D},
    )
    result.trial_granted = True
    await session.flush()
    return result

"""Агрегаты подписок для админки."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Event, User
from services.subscription import (
    PAID_PLANS,
    PLAN_CATALOG,
    PLAN_FREEMIUM,
    PLAN_TRIAL_7D,
    PLAN_UNLIMITED,
    RETAIL_PLAN_ORDER,
    is_paid_plan_active,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _expires(user: User) -> datetime | None:
    exp = user.tariff_expires_at
    if exp is None:
        return None
    if exp.tzinfo is None:
        return exp.replace(tzinfo=timezone.utc)
    return exp


def _is_retail_paid_plan(plan: str) -> bool:
    p = (plan or "").lower()
    return p in PAID_PLANS and p not in (PLAN_FREEMIUM, PLAN_TRIAL_7D)


async def build_subscription_stats(session: AsyncSession) -> dict:
    now = _utc_now()
    result = await session.execute(select(User))
    users = list(result.scalars().all())

    by_plan: dict[str, int] = {}
    active_by_plan: dict[str, int] = {}
    expired_by_plan: dict[str, int] = {}

    startify_users = 0
    with_kaspi = 0
    active_trial = 0
    expired_trial = 0
    active_paid_retail = 0
    ever_paid_retail = 0
    active_unlimited = 0
    revenue_active_kzt = 0

    for user in users:
        plan = (user.tariff_plan or PLAN_FREEMIUM).lower()
        by_plan[plan] = by_plan.get(plan, 0) + 1

        active = is_paid_plan_active(user, now=now)
        if active:
            active_by_plan[plan] = active_by_plan.get(plan, 0) + 1
        elif plan not in (PLAN_FREEMIUM,) and _expires(user) and _expires(user) < now:
            expired_by_plan[plan] = expired_by_plan.get(plan, 0) + 1

        if (user.partner_source or "").lower() == "startify":
            startify_users += 1
        if user.kaspi_phone:
            with_kaspi += 1

        if plan == PLAN_TRIAL_7D:
            if active:
                active_trial += 1
            elif _expires(user) and _expires(user) < now:
                expired_trial += 1

        if _is_retail_paid_plan(plan):
            ever_paid_retail += 1
            if active:
                active_paid_retail += 1
                meta = PLAN_CATALOG.get(plan) or {}
                revenue_active_kzt += int(meta.get("priceKzt") or 0)
            if plan == PLAN_UNLIMITED and active:
                active_unlimited += 1

    trial_granted_events = await session.execute(
        select(func.count()).select_from(Event).where(Event.event_type == "subscription_trial_granted")
    )
    trials_from_events = int(trial_granted_events.scalar_one())

    return {
        "totalUsers": len(users),
        "startifyUsers": startify_users,
        "withKaspiPhone": with_kaspi,
        "byPlan": by_plan,
        "activeByPlan": active_by_plan,
        "expiredByPlan": expired_by_plan,
        "activeTrial": active_trial,
        "expiredTrial": expired_trial,
        "trialsGrantedEvents": trials_from_events,
        "everPaidRetail": ever_paid_retail,
        "activePaidRetail": active_paid_retail,
        "activeUnlimited": active_unlimited,
        "revenueActiveKzt": revenue_active_kzt,
        "freemium": by_plan.get(PLAN_FREEMIUM, 0),
    }


def format_subscription_stats_report(stats: dict) -> str:
    lines = [
        "💳 <b>Подписки Lumo</b>",
        "",
        f"👥 Всего пользователей: <b>{stats['totalUsers']}</b>",
        f"🔗 С Startify (utm): <b>{stats['startifyUsers']}</b>",
        f"📱 Указали Kaspi-телефон: <b>{stats['withKaspiPhone']}</b>",
        "",
        "<b>Купили (платные тарифы, не trial):</b>",
        f"  • когда-либо: <b>{stats['everPaidRetail']}</b>",
        f"  • сейчас активны: <b>{stats['activePaidRetail']}</b>",
        f"  • безлимит активен: <b>{stats['activeUnlimited']}</b>",
        f"  • сумма активных (разово): <b>{stats['revenueActiveKzt']:,} ₸</b>".replace(",", " "),
        "",
        "<b>Trial 7 дней:</b>",
        f"  • активен сейчас: <b>{stats['activeTrial']}</b>",
        f"  • истёк: <b>{stats['expiredTrial']}</b>",
        f"  • выдано (события): <b>{stats['trialsGrantedEvents']}</b>",
        "",
        "<b>По тарифам (все / активные):</b>",
    ]

    plan_order = [PLAN_FREEMIUM, PLAN_TRIAL_7D, *RETAIL_PLAN_ORDER]
    seen: set[str] = set()
    for plan_id in plan_order:
        seen.add(plan_id)
        total = stats["byPlan"].get(plan_id, 0)
        if total == 0 and plan_id not in stats["byPlan"]:
            continue
        active = stats["activeByPlan"].get(plan_id, 0)
        label = (PLAN_CATALOG.get(plan_id) or {}).get("label", plan_id)
        expired = stats["expiredByPlan"].get(plan_id, 0)
        extra = f", истекло {expired}" if expired else ""
        lines.append(f"  • {label}: {total} (активно {active}{extra})")

    for plan_id, total in sorted(stats["byPlan"].items()):
        if plan_id in seen:
            continue
        active = stats["activeByPlan"].get(plan_id, 0)
        lines.append(f"  • {plan_id}: {total} (активно {active})")

    lines.extend(
        [
            "",
            f"🆓 Freemium: <b>{stats['freemium']}</b>",
            "",
            "<i>Оплата через Startify → PUT /partner/v1/users/…/subscription</i>",
        ]
    )
    return "\n".join(lines)

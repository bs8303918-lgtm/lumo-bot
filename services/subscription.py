"""Subscription plans and access checks (Startify B2B)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from config import get_settings
from db.models import User

PLAN_FREEMIUM = "freemium"
PLAN_TRIAL_7D = "trial_7d"
PLAN_1M = "plan_1m"
PLAN_3M = "plan_3m"
PLAN_6M = "plan_6m"
PLAN_12M = "plan_12m"
PLAN_UNLIMITED = "unlimited"

PAID_PLANS = frozenset({PLAN_TRIAL_7D, PLAN_1M, PLAN_3M, PLAN_6M, PLAN_12M, PLAN_UNLIMITED})

RETAIL_PLAN_ORDER = (PLAN_1M, PLAN_3M, PLAN_6M, PLAN_12M, PLAN_UNLIMITED)

# Цены для Mini App и Startify
PLAN_CATALOG: dict[str, dict] = {
    PLAN_FREEMIUM: {
        "id": PLAN_FREEMIUM,
        "label": "Бесплатно",
        "durationDays": None,
        "priceKzt": 0,
        "aiDailyLimit": 3,
        "description": "3 AI-запроса в день · каталог · уведомления",
        "benefit": None,
    },
    PLAN_TRIAL_7D: {
        "id": PLAN_TRIAL_7D,
        "label": "Пробный 7 дней",
        "durationDays": 7,
        "priceKzt": 0,
        "aiDailyLimit": 999,
        "description": "Полный доступ на неделю",
        "benefit": None,
    },
    PLAN_1M: {
        "id": PLAN_1M,
        "label": "1 месяц",
        "durationDays": 30,
        "priceKzt": 990,
        "aiDailyLimit": 999,
        "description": "Без лимита AI-поиска",
        "benefit": None,
    },
    PLAN_3M: {
        "id": PLAN_3M,
        "label": "3 месяца",
        "durationDays": 90,
        "priceKzt": 4990,
        "aiDailyLimit": 999,
        "description": "Без лимита AI-поиска",
        "benefit": None,
    },
    PLAN_6M: {
        "id": PLAN_6M,
        "label": "6 месяцев",
        "durationDays": 180,
        "priceKzt": 7990,
        "aiDailyLimit": 999,
        "description": "Тариф «Старт»",
        "benefit": "Экономия 1 990 ₸",
    },
    PLAN_12M: {
        "id": PLAN_12M,
        "label": "12 месяцев",
        "durationDays": 365,
        "priceKzt": 11880,
        "aiDailyLimit": 999,
        "description": "Лучшая цена за год",
        "benefit": "990 ₸/мес",
    },
    PLAN_UNLIMITED: {
        "id": PLAN_UNLIMITED,
        "label": "Безлимит",
        "durationDays": None,
        "priceKzt": 49000,
        "aiDailyLimit": 999,
        "description": "Разовая покупка навсегда",
        "benefit": "Навсегда",
    },
}

DEEP_LINK_PREFIX = "sf"


def normalize_plan_id(raw: str | None) -> str | None:
    if not raw:
        return None
    plan = raw.strip().lower().replace("-", "_")
    aliases = {
        "1m": PLAN_1M,
        "month": PLAN_1M,
        "7d": PLAN_TRIAL_7D,
        "trial": PLAN_TRIAL_7D,
        "3m": PLAN_3M,
        "6m": PLAN_6M,
        "12m": PLAN_12M,
        "forever": PLAN_UNLIMITED,
        "lifetime": PLAN_UNLIMITED,
    }
    if plan in aliases:
        return aliases[plan]
    if plan in PLAN_CATALOG:
        return plan
    return None


def parse_startify_payload(payload: str) -> tuple[str | None, str | None]:
    """
    Deep link: sf_ref_campaign_3m → (ref=campaign, pending_plan=plan_3m)
    Formats: sf_3m | sf_ref_home | sf_ref_home_3m
    """
    text = (payload or "").strip()
    if not text.lower().startswith(DEEP_LINK_PREFIX):
        return None, None
    parts = [p for p in text.split("_") if p]
    if len(parts) < 2:
        return None, None

    ref: str | None = None
    pending_plan: str | None = None
    idx = 1
    if parts[idx].lower() == "ref" and len(parts) > idx + 1:
        ref = parts[idx + 1]
        idx += 2
    if idx < len(parts):
        pending_plan = normalize_plan_id("_".join(parts[idx:]))
    return ref, pending_plan


def plan_duration(plan_id: str) -> timedelta | None:
    meta = PLAN_CATALOG.get(plan_id) or {}
    days = meta.get("durationDays")
    if days is None:
        return None if plan_id != PLAN_UNLIMITED else None
    return timedelta(days=int(days))


def expires_at_for_plan(plan_id: str, *, from_dt: datetime | None = None) -> datetime | None:
    if plan_id == PLAN_FREEMIUM:
        return None
    if plan_id == PLAN_UNLIMITED:
        return None
    delta = plan_duration(plan_id)
    if delta is None:
        return None
    start = from_dt or datetime.now(timezone.utc)
    return start + delta


def is_paid_plan_active(user: User, *, now: datetime | None = None) -> bool:
    plan = (user.tariff_plan or PLAN_FREEMIUM).lower()
    if plan == PLAN_FREEMIUM:
        return False
    if plan == PLAN_UNLIMITED:
        return True
    expires = user.tariff_expires_at
    if expires is None:
        return plan in PAID_PLANS
    now = now or datetime.now(timezone.utc)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires > now


def effective_ai_daily_limit(user: User, *, telegram_id: int | None = None) -> int:
    settings = get_settings()
    if telegram_id is not None and settings.is_admin(telegram_id):
        return 999999
    if not settings.subscriptions_enforced:
        return settings.ai_search_daily_limit
    if is_paid_plan_active(user):
        meta = PLAN_CATALOG.get(user.tariff_plan or "", {})
        return int(meta.get("aiDailyLimit") or 999)
    return settings.ai_search_daily_limit


def subscription_status(user: User) -> dict:
    settings = get_settings()
    plan = (user.tariff_plan or PLAN_FREEMIUM).lower()
    active = is_paid_plan_active(user)
    expires = user.tariff_expires_at
    expires_iso = None
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        expires_iso = expires.isoformat()

    return {
        "plan": plan,
        "planLabel": (PLAN_CATALOG.get(plan) or {}).get("label", plan),
        "isActive": active,
        "isPaid": plan in PAID_PLANS and active,
        "expiresAt": expires_iso,
        "partnerSource": user.partner_source,
        "partnerRef": user.partner_ref,
        "kaspiPhone": user.kaspi_phone,
        "enforced": settings.subscriptions_enforced,
        "aiDailyLimit": effective_ai_daily_limit(user, telegram_id=user.telegram_id),
    }


def public_plans() -> list[dict]:
    settings = get_settings()
    checkout = settings.startify_checkout_url.strip()
    items = []
    for plan_id in RETAIL_PLAN_ORDER:
        meta = PLAN_CATALOG.get(plan_id)
        if not meta:
            continue
        row = dict(meta)
        row["checkoutUrl"] = checkout or None
        items.append(row)
    return items

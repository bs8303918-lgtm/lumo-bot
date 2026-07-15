"""B2B API for AI Startify (NestJS + Prisma + Postgres on their side)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from api.partner_auth import require_partner_api_key
from db.models import User
from db.repositories.users import UserRepository
from services.opportunity_catalog import catalog_repo
from services.subscription import (
    PLAN_FREEMIUM,
    PLAN_UNLIMITED,
    expires_at_for_plan,
    normalize_plan_id,
    subscription_status,
)
from services.subscription_grant import clear_subscription_push_flags
from services.webapp_catalog import dedupe_opportunities, serialize_opportunity, sort_opportunities_by_deadline

router = APIRouter(prefix="/partner/v1", tags=["partner-startify"])

VALID_PLANS = frozenset(
    {"freemium", "trial_7d", "plan_1m", "plan_3m", "plan_6m", "plan_12m", "unlimited"}
)


class SubscriptionUpsert(BaseModel):
    tariffPlan: str = Field(min_length=2, max_length=32)
    expiresAt: datetime | None = None
    kaspiPhone: str | None = Field(default=None, max_length=32)
    partnerRef: str | None = Field(default=None, max_length=128)
    partnerSource: str = Field(default="startify", max_length=64)


class AttributionBody(BaseModel):
    partnerSource: str = Field(default="startify", max_length=64)
    partnerRef: str | None = Field(default=None, max_length=128)


def _serialize_user(user: User) -> dict:
    return {
        "telegramId": user.telegram_id,
        "username": user.username,
        "subscription": subscription_status(user),
    }


@router.get("/health")
async def partner_health(_: None = Depends(require_partner_api_key)) -> dict:
    return {"ok": True, "service": "lumo-partner-api", "version": 1}


@router.get("/users/{telegram_id}")
async def partner_get_user(
    telegram_id: int,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_partner_api_key),
) -> dict:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(user)


@router.put("/users/{telegram_id}/subscription")
async def partner_upsert_subscription(
    telegram_id: int,
    payload: SubscriptionUpsert,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_partner_api_key),
) -> dict:
    plan = normalize_plan_id(payload.tariffPlan) or payload.tariffPlan.lower().strip()
    if plan not in VALID_PLANS:
        raise HTTPException(status_code=422, detail=f"Unknown tariff plan: {payload.tariffPlan}")

    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(telegram_id)
    if not user:
        user, _ = await repo.get_or_create(telegram_id, None)

    user.partner_source = payload.partnerSource or user.partner_source or "startify"
    if payload.partnerRef:
        user.partner_ref = payload.partnerRef
    user.tariff_plan = plan
    if payload.kaspiPhone:
        user.kaspi_phone = payload.kaspiPhone

    if plan == PLAN_FREEMIUM:
        user.tariff_expires_at = None
    elif plan == PLAN_UNLIMITED:
        user.tariff_expires_at = None
    elif payload.expiresAt is not None:
        user.tariff_expires_at = payload.expiresAt
    else:
        user.tariff_expires_at = expires_at_for_plan(plan)

    await clear_subscription_push_flags(session, user.id)
    await session.flush()
    return {"ok": True, "user": _serialize_user(user)}


@router.post("/users/{telegram_id}/attribution")
async def partner_set_attribution(
    telegram_id: int,
    payload: AttributionBody,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_partner_api_key),
) -> dict:
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(telegram_id)
    if not user:
        user, _ = await repo.get_or_create(telegram_id, None)
    user.partner_source = payload.partnerSource
    if payload.partnerRef:
        user.partner_ref = payload.partnerRef
    await session.flush()
    return {"ok": True, "user": _serialize_user(user)}


@router.get("/catalog/opportunities")
async def partner_export_catalog(
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_partner_api_key),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Выгрузка каталога Lumo для синка на сайт Startify (без AI, только JSON)."""
    repo = catalog_repo(session)
    items = sort_opportunities_by_deadline(dedupe_opportunities(await repo.list_all_public_active()))
    total = len(items)
    page = items[offset : offset + limit]
    return {
        "items": [serialize_opportunity(entry) for entry in page],
        "total": total,
        "offset": offset,
        "limit": limit,
        "hasMore": offset + limit < total,
    }

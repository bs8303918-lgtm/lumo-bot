from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.event_types import CATALOG_APPLY_CLICK, CATALOG_TELEGRAM_CLICK
from api.auth import get_current_user, require_admin
from api.deps import get_db
from db.models import User
from db.repositories.traction_analytics import TractionAnalyticsRepository
from db.repositories.users import EventRepository

router = APIRouter(tags=["traction"])


class TrackClickRequest(BaseModel):
    type: Literal["apply", "telegram"] = "apply"
    catalogId: int = Field(ge=1)


@router.post("/lumo/track-click")
async def track_catalog_click(
    payload: TrackClickRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    event_type = CATALOG_APPLY_CLICK if payload.type == "apply" else CATALOG_TELEGRAM_CLICK
    await EventRepository(session).log(
        event_type,
        user_id=user.id,
        related_id=payload.catalogId,
        metadata={"source": "mini_app"},
    )
    await session.commit()
    return {"ok": True}


@router.get("/admin/traction")
async def admin_traction(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
    days: int = Query(default=30, ge=0, le=365),
) -> dict:
    return await TractionAnalyticsRepository(session).build_dashboard(days=days)

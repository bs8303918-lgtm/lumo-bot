from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_admin
from api.deps import get_db
from db.models import User
from db.repositories.feedback import FeedbackRepository
from services.admin_interest_prompts import build_interest_prompts_dashboard
from services.admin_tracking import build_tracking_dashboard
from services.admin_notify import notify_admin

router = APIRouter(tags=["admin-tracking"])


class FeedbackRequest(BaseModel):
    kind: Literal["bug", "idea"] = "bug"
    message: str = Field(min_length=5, max_length=4000)


@router.get("/admin/tracking")
async def admin_tracking(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await build_tracking_dashboard(session)


@router.get("/admin/interest-prompts")
async def admin_interest_prompts(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
    search: str = Query(default="", max_length=200),
    category: str = Query(default="", max_length=64),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return await build_interest_prompts_dashboard(
        session,
        search=search,
        category=category,
        limit=limit,
        offset=offset,
    )


@router.post("/feedback")
async def submit_feedback(
    payload: FeedbackRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    row = await FeedbackRepository(session).create(
        kind=payload.kind,
        message=payload.message,
        user_id=user.id,
        username=user.username,
        source="mini_app",
    )
    await session.commit()

    label = "🐛 Баг" if payload.kind == "bug" else "💡 Идея"
    user_ref = f"@{user.username}" if user.username else f"id{user.telegram_id}"
    preview = payload.message.strip()
    if len(preview) > 200:
        preview = preview[:200] + "…"
    await notify_admin(f"{label} от {user_ref} (Mini App)\n\n{preview}")

    return {"ok": True, "id": row.id}

import re

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_admin
from api.deps import get_db
from db.models import User
from db.repositories.opportunity_catalog import OPPORTUNITY_TYPES
from db.repositories.submissions import SubmissionRepository
from services.admin_notify import notify_admin
from services.submission_service import (
    approve_submission,
    reject_submission,
    serialize_submission,
)

router = APIRouter(tags=["submissions"])

VALID_TYPES = [t for t in OPPORTUNITY_TYPES if t != "другое"]
_CUSTOM_TYPE_RE = re.compile(r"^[\w\s\-]{2,32}$", re.UNICODE)


def _normalize_custom_type(raw: str) -> str:
    return " ".join(raw.strip().split()).lower()


class SubmitOpportunityRequest(BaseModel):
    sourceMode: Literal["manual", "channel"] = "manual"
    title: str | None = Field(default=None, max_length=512)
    type: str | None = Field(default=None, max_length=64)
    customType: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=4000)
    deadline: str | None = Field(default=None, max_length=128)
    location: str | None = Field(default=None, max_length=255)
    link: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def validate_payload(self) -> "SubmitOpportunityRequest":
        link = (self.link or "").strip()
        if self.sourceMode == "channel":
            if not link:
                raise ValueError("Укажи ссылку на пост или канал")
            return self

        title = (self.title or "").strip()
        opp_type = (self.type or "").strip().lower()
        if len(title) < 3:
            raise ValueError("Название — минимум 3 символа")
        if opp_type == "другое":
            custom = _normalize_custom_type(self.customType or "")
            if not _CUSTOM_TYPE_RE.match(custom):
                raise ValueError("Напиши свою категорию (2–32 символа, буквы и цифры)")
            self.title = title
            self.type = custom
            return self
        if opp_type not in VALID_TYPES:
            raise ValueError("Выбери категорию")
        self.title = title
        self.type = opp_type
        return self


class RejectSubmissionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


@router.post("/lumo/submissions")
async def submit_opportunity(
    payload: SubmitOpportunityRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    repo = SubmissionRepository(session)
    row = await repo.create(
        user_id=user.id,
        source_mode=payload.sourceMode,
        title=(payload.title or "").strip() or None,
        opportunity_type=(payload.type or "").strip().lower() or None,
        description=(payload.description or "").strip() or None,
        deadline=(payload.deadline or "").strip() or None,
        location=(payload.location or "").strip() or None,
        link=(payload.link or "").strip() or None,
    )
    await session.commit()

    user_ref = f"@{user.username}" if user.username else f"id{user.telegram_id}"
    mode_label = "вручную" if payload.sourceMode == "manual" else "из канала"
    title_line = row.title or row.link or "—"
    await notify_admin(
        f"📥 Новая заявка ({mode_label}) от {user_ref}\n\n"
        f"«{title_line}»\n"
        f"Тип: {row.opportunity_type or '—'}\n"
        f"ID: {row.id} · Mini App → Админ"
    )

    return {
        "ok": True,
        "id": row.id,
        "message": "Отправлено на проверку. Опубликуем после модерации.",
    }


@router.get("/lumo/submissions/mine")
async def my_submissions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = await SubmissionRepository(session).list_for_user(user.id)
    return [serialize_submission(row) for row in rows]


@router.get("/admin/submissions")
async def admin_list_submissions(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
    status: str = "pending",
) -> dict:
    repo = SubmissionRepository(session)
    rows = await repo.list_by_status(status, limit=40)
    pending_count = await repo.count_pending()
    return {
        "pendingCount": pending_count,
        "items": [serialize_submission(row, include_user=True) for row in rows],
    }


@router.post("/admin/submissions/{submission_id}/approve")
async def admin_approve_submission(
    submission_id: int,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    try:
        entry = await approve_submission(session, submission_id)
    except ValueError as exc:
        code = str(exc)
        if code == "not_found":
            raise HTTPException(status_code=404, detail="Заявка не найдена") from exc
        raise HTTPException(status_code=409, detail="Заявка уже обработана") from exc
    await session.commit()
    return {"ok": True, "catalogId": entry.id, "title": entry.title}


@router.post("/admin/submissions/{submission_id}/reject")
async def admin_reject_submission(
    submission_id: int,
    payload: RejectSubmissionRequest,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    try:
        row = await reject_submission(session, submission_id, admin_note=payload.note)
    except ValueError as exc:
        code = str(exc)
        if code == "not_found":
            raise HTTPException(status_code=404, detail="Заявка не найдена") from exc
        raise HTTPException(status_code=409, detail="Заявка уже обработана") from exc
    await session.commit()
    return {"ok": True, "id": row.id}

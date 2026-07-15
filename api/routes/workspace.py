"""Mentor workspace API — kanban, shortlists, profile evaluator."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.deps import get_db
from db.models import User
from db.repositories.mentor_workspace import KANBAN_STATUSES, MentorWorkspaceRepository
from services.opportunity_catalog import catalog_repo
from services.profile_evaluator import evaluate_profile_fit
from services.webapp_catalog import serialize_opportunity

router = APIRouter(tags=["workspace"])

KANBAN_LABELS = {
    "todo": "Нужно подать",
    "in_progress": "В процессе",
    "submitted": "Подано",
}


class ApplicationCreateRequest(BaseModel):
    catalogId: int
    studentName: str = Field(default="Студент", max_length=120)
    studentUserId: int | None = Field(default=None, ge=1)
    status: str = Field(default="todo")
    notes: str | None = Field(default=None, max_length=2000)


class ApplicationUpdateRequest(BaseModel):
    status: str | None = None
    studentName: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class ShortlistCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    agencyName: str = Field(default="Lumo", max_length=120)
    catalogIds: list[int] = Field(min_length=1, max_length=30)


class EvaluateRequest(BaseModel):
    catalogId: int
    studentProfile: str | None = Field(default=None, max_length=4000)


async def _load_opportunity(session: AsyncSession, user: User, catalog_id: int):
    repo = catalog_repo(session)
    row = await repo.get_entry_with_channel(catalog_id)
    if not row:
        raise HTTPException(status_code=404, detail="Программа не найдена")
    entry, _channel = row
    if not entry.is_active:
        raise HTTPException(status_code=404, detail="Программа не найдена")
    if not await repo.user_can_access_entry(user.id, entry.id):
        raise HTTPException(status_code=403, detail="Нет доступа к программе")
    return entry


async def _serialize_application(session: AsyncSession, user: User, app) -> dict:
    entry = await _load_opportunity(session, user, app.catalog_id)
    opp = serialize_opportunity(entry)
    return {
        "id": app.id,
        "catalogId": app.catalog_id,
        "studentName": app.student_name,
        "status": app.status,
        "statusLabel": KANBAN_LABELS.get(app.status, app.status),
        "notes": app.notes,
        "updatedAt": app.updated_at.isoformat() if app.updated_at else None,
        "opportunity": {
            "id": opp["id"],
            "title": opp["title"],
            "type": opp["type"],
            "label": opp["label"],
            "emoji": opp["emoji"],
            "deadlineLabel": opp["deadlineLabel"],
            "deadlineUrgent": opp["deadlineUrgent"],
            "applicationUrl": opp.get("applicationUrl"),
        },
    }


@router.get("/workspace/meta")
async def workspace_meta() -> dict:
    return {
        "kanbanStatuses": [
            {"id": status, "label": KANBAN_LABELS[status]} for status in KANBAN_STATUSES
        ],
    }


@router.get("/workspace/applications")
async def list_applications(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    repo = MentorWorkspaceRepository(session)
    apps = await repo.list_applications(user.id)
    items = []
    for app in apps:
        try:
            items.append(await _serialize_application(session, user, app))
        except HTTPException:
            continue
    return {"items": items, "total": len(items)}


@router.post("/workspace/applications")
async def create_application(
    body: ApplicationCreateRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if body.status not in KANBAN_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    await _load_opportunity(session, user, body.catalogId)
    repo = MentorWorkspaceRepository(session)
    app = await repo.upsert_application(
        user.id,
        catalog_id=body.catalogId,
        student_name=body.studentName.strip() or "Студент",
        student_user_id=body.studentUserId,
        status=body.status,
        notes=body.notes,
    )
    await session.commit()
    return {"application": await _serialize_application(session, user, app)}


@router.patch("/workspace/applications/{app_id}")
async def update_application(
    app_id: int,
    body: ApplicationUpdateRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    repo = MentorWorkspaceRepository(session)
    app = await repo.get_application(user.id, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    if body.status and body.status not in KANBAN_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    app = await repo.update_application(
        app,
        status=body.status,
        student_name=body.studentName.strip() if body.studentName else None,
        notes=body.notes,
    )
    await session.commit()
    return {"application": await _serialize_application(session, user, app)}


@router.delete("/workspace/applications/{app_id}")
async def delete_application(
    app_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    repo = MentorWorkspaceRepository(session)
    app = await repo.get_application(user.id, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    await repo.delete_application(app)
    await session.commit()
    return {"ok": True}


@router.get("/workspace/shortlists")
async def list_shortlists(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    repo = MentorWorkspaceRepository(session)
    rows = await repo.list_shortlists(user.id)
    return {
        "items": [
            {
                "id": row.id,
                "title": row.title,
                "agencyName": row.agency_name,
                "slug": row.slug,
                "createdAt": row.created_at.isoformat() if row.created_at else None,
                "sharePath": f"/shortlist/{row.slug}",
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.post("/workspace/shortlists")
async def create_shortlist(
    body: ShortlistCreateRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    catalog_ids = list(dict.fromkeys(body.catalogIds))
    for catalog_id in catalog_ids:
        await _load_opportunity(session, user, catalog_id)

    repo = MentorWorkspaceRepository(session)
    shortlist = await repo.create_shortlist(
        user.id,
        title=body.title.strip(),
        agency_name=body.agencyName.strip() or "Lumo",
        catalog_ids=catalog_ids,
    )
    await session.commit()
    return {
        "shortlist": {
            "id": shortlist.id,
            "title": shortlist.title,
            "agencyName": shortlist.agency_name,
            "slug": shortlist.slug,
            "sharePath": f"/shortlist/{shortlist.slug}",
        },
        "message": "Подборка готова — открой ссылку или сохрани в PDF через печать",
    }


@router.get("/workspace/shortlist/{slug}")
async def get_public_shortlist(
    slug: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    repo = MentorWorkspaceRepository(session)
    shortlist = await repo.get_shortlist_by_slug(slug.strip())
    if not shortlist:
        raise HTTPException(status_code=404, detail="Подборка не найдена")

    items = []
    for item in sorted(shortlist.items, key=lambda x: x.sort_order):
        row = await catalog_repo(session).get_entry_with_channel(item.catalog_id)
        if not row:
            continue
        entry, _channel = row
        if not entry.is_active:
            continue
        items.append(serialize_opportunity(entry))

    return {
        "title": shortlist.title,
        "agencyName": shortlist.agency_name,
        "slug": shortlist.slug,
        "createdAt": shortlist.created_at.isoformat() if shortlist.created_at else None,
        "items": items,
        "total": len(items),
    }


@router.post("/workspace/evaluate")
async def evaluate_opportunity(
    body: EvaluateRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    entry = await _load_opportunity(session, user, body.catalogId)
    profile = (body.studentProfile or user.interest_query or "").strip()
    result = await evaluate_profile_fit(profile, entry)
    opp = serialize_opportunity(entry)
    return {
        "catalogId": entry.id,
        "opportunityTitle": opp["title"],
        "studentProfile": profile,
        **result,
    }

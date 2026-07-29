import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_admin
from api.deps import get_db, require_premium_access
from api.schemas import MessageResponse
from db.models import CatalogCategory, CatalogEditLog, CatalogOpportunity, User
from db.repositories.catalog import GrantRepository
from llm.client import LLMClient
from services.interest_matcher import CATEGORY_DISPLAY, OPPORTUNITY_TYPES
from services.opportunity_catalog import catalog_repo
from services.webapp_catalog import serialize_opportunity

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/sync-from-bot", response_model=MessageResponse, dependencies=[Depends(require_premium_access)])
async def sync_grants_from_bot(session: AsyncSession = Depends(get_db)) -> dict:
    imported = await GrantRepository(session).import_from_sent_matches()
    return {
        "ok": True,
        "message": f"Imported {imported} grants from bot feed.",
    }


class ManualOpportunityRequest(BaseModel):
    title: str
    description: str = ""
    deadline: str = "не указан"
    opportunityType: str = "конкурс"
    requirements: str | None = None
    country: str | None = None
    applicationUrl: str | None = None
    messageLink: str | None = None
    sourceChannelName: str | None = None


@router.post("/opportunities")
async def create_manual_opportunity(
    payload: ManualOpportunityRequest,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    entry = await catalog_repo(session).create_manual_entry(
        title=payload.title.strip(),
        description=payload.description.strip(),
        deadline=payload.deadline.strip() or "не указан",
        opportunity_type=payload.opportunityType,
        requirements=(payload.requirements or "").strip() or None,
        country=(payload.country or "").strip() or None,
        application_url=(payload.applicationUrl or "").strip() or None,
        message_link=(payload.messageLink or "").strip() or None,
        source_channel_name=(payload.sourceChannelName or "").strip() or None,
    )
    await session.commit()
    return serialize_opportunity(entry)


@router.get("/opportunities")
async def list_admin_opportunities(
    q: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Admin browse/search across ALL catalog entries (active or not) for the edit workspace."""
    result = await session.execute(
        select(CatalogOpportunity).order_by(CatalogOpportunity.classified_at.desc()).limit(500)
    )
    entries = list(result.scalars().all())
    if q:
        needle = q.strip().lower()
        entries = [
            e
            for e in entries
            if needle in (e.title or "").lower() or needle in (e.source_channel_name or "").lower()
        ]
    entries = entries[:limit]
    return {"items": [serialize_opportunity(e) for e in entries]}


_EDIT_FIELD_MAP = {
    "title": "title",
    "description": "description",
    "deadline": "deadline",
    "opportunityType": "opportunity_type",
    "requirements": "requirements",
    "country": "country",
    "applicationUrl": "application_url",
    "messageLink": "message_link",
    "sourceChannelName": "source_channel_name",
    "isActive": "is_active",
}


class EditOpportunityRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    deadline: str | None = None
    opportunityType: str | None = None
    requirements: str | None = None
    country: str | None = None
    applicationUrl: str | None = None
    messageLink: str | None = None
    sourceChannelName: str | None = None
    isActive: bool | None = None


@router.patch("/opportunities/{item_id}")
async def edit_opportunity(
    item_id: int,
    payload: EditOpportunityRequest,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Edit an existing catalog entry, recording a diff in catalog_edit_log for future AI training."""
    entry = await catalog_repo(session).get_by_id(item_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")

    changes: dict[str, list] = {}
    for field, attr in _EDIT_FIELD_MAP.items():
        if field not in payload.model_fields_set:
            continue
        value = getattr(payload, field)
        old_value = getattr(entry, attr)
        if old_value != value:
            changes[attr] = [old_value, value]
            setattr(entry, attr, value)

    if changes:
        session.add(
            CatalogEditLog(
                opportunity_id=entry.id,
                admin_user_id=admin.id,
                changes_json=json.dumps(changes, ensure_ascii=False),
            )
        )
    await session.commit()
    await session.refresh(entry)
    return serialize_opportunity(entry)


class DuplicateCheckRequest(BaseModel):
    title: str
    description: str = ""
    applicationUrl: str | None = None


@router.post("/opportunities/check-duplicate")
async def check_duplicate_opportunity(
    payload: DuplicateCheckRequest,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    duplicate = await catalog_repo(session).find_active_duplicate(
        payload.title, payload.applicationUrl, payload.description
    )
    return {"duplicate": serialize_opportunity(duplicate) if duplicate else None}


class ExtractRequest(BaseModel):
    text: str


def _map_extracted(item: dict) -> dict:
    return {
        "title": item.get("title") or "",
        "description": item.get("description") or "",
        "deadline": item.get("deadline") or "не указан",
        "opportunityType": item.get("type") or "конкурс",
        "requirements": item.get("requirements"),
        "country": item.get("country"),
        "applicationUrl": item.get("application_url"),
    }


@router.post("/opportunities/extract")
async def extract_opportunities_from_text(
    payload: ExtractRequest,
    _admin: User = Depends(require_admin),
) -> dict:
    """Feed pasted document/post text through the same LLM classifier used for Telegram
    posts, returning draft cards for the admin to review, edit, and publish — instead of
    persisting anything directly."""
    text = payload.text.strip()
    if len(text) < 20:
        raise HTTPException(status_code=422, detail="Слишком мало текста для анализа")

    data, _raw = await LLMClient().classify_opportunity(text)
    if not data or not data.get("is_opportunity"):
        return {"items": []}

    raw_items = data.get("opportunities") or [data]
    return {"items": [_map_extracted(item) for item in raw_items if item.get("title")]}


class CategoryRequest(BaseModel):
    type: str
    label: str
    emoji: str = "📌"


@router.get("/categories")
async def list_admin_categories(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    result = await session.execute(select(CatalogCategory).order_by(CatalogCategory.created_at.asc()))
    custom = [
        {"type": c.type, "label": c.label, "emoji": c.emoji, "custom": True} for c in result.scalars().all()
    ]
    builtin = [
        {
            "type": t,
            "emoji": CATEGORY_DISPLAY.get(t, ("📌", t.capitalize()))[0],
            "label": CATEGORY_DISPLAY.get(t, ("📌", t.capitalize()))[1],
            "custom": False,
        }
        for t in OPPORTUNITY_TYPES
        if t != "другое"
    ]
    return {"items": builtin + custom}


@router.post("/categories")
async def create_admin_category(
    payload: CategoryRequest,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    type_id = payload.type.strip().lower().replace(" ", "_")
    if not type_id:
        raise HTTPException(status_code=422, detail="Укажи тип категории")

    existing = await session.execute(select(CatalogCategory).where(CatalogCategory.type == type_id))
    if existing.scalar_one_or_none() or type_id in OPPORTUNITY_TYPES:
        raise HTTPException(status_code=409, detail="Такая категория уже существует")

    category = CatalogCategory(
        type=type_id,
        label=payload.label.strip() or type_id,
        emoji=payload.emoji.strip() or "📌",
    )
    session.add(category)
    await session.commit()
    return {"type": category.type, "label": category.label, "emoji": category.emoji, "custom": True}

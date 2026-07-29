from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_admin
from api.deps import get_db, require_premium_access
from api.schemas import MessageResponse
from db.models import User
from db.repositories.catalog import GrantRepository
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

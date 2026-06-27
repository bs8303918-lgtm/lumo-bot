from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_premium_access
from api.schemas import MessageResponse
from db.repositories.catalog import GrantRepository

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/sync-from-bot", response_model=MessageResponse, dependencies=[Depends(require_premium_access)])
async def sync_grants_from_bot(session: AsyncSession = Depends(get_db)) -> dict:
    imported = await GrantRepository(session).import_from_sent_matches()
    return {
        "ok": True,
        "message": f"Imported {imported} grants from bot feed.",
    }

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, has_premium_access
from api.schemas import GrantDetail, GrantListItem
from db.repositories.catalog import GrantRepository

router = APIRouter(prefix="/grants", tags=["grants"])


@router.get("", response_model=list[GrantListItem])
async def list_grants(
    q: str | None = Query(default=None, description="Search by title, location, or description"),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    repo = GrantRepository(session)
    return await repo.list_published(query=q)


@router.get("/{grant_id}", response_model=GrantDetail)
async def get_grant(
    grant_id: int,
    session: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> dict:
    repo = GrantRepository(session)
    unlocked = has_premium_access(authorization)
    grant = await repo.get_published(grant_id, include_premium=unlocked)
    if not grant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")
    return grant

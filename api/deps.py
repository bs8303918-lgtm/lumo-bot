from collections.abc import AsyncGenerator

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.base import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def has_premium_access(authorization: str | None = Header(default=None)) -> bool:
    settings = get_settings()
    token = settings.api_access_token.strip()
    if not token:
        return False
    if not authorization:
        return False
    prefix = "Bearer "
    if authorization.startswith(prefix):
        return authorization[len(prefix) :] == token
    return authorization == token


def require_premium_access(authorization: str | None = Header(default=None)) -> None:
    if not has_premium_access(authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Premium access required. Join the community or provide a valid access token.",
        )

"""Apply Startify deep-link payload on /start."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User
from services.subscription_trial import StartifyStartResult, apply_startify_start


async def apply_start_payload(
    session: AsyncSession,
    user: User,
    payload: str | None,
) -> StartifyStartResult:
    return await apply_startify_start(session, user, payload)

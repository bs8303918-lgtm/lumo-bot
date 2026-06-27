"""Apply Startify deep-link payload on /start."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User
from services.subscription import DEEP_LINK_PREFIX, parse_startify_payload


async def apply_start_payload(session: AsyncSession, user: User, payload: str | None) -> None:
    if not payload or not payload.strip().lower().startswith(DEEP_LINK_PREFIX):
        return
    ref, _pending = parse_startify_payload(payload.strip())
    user.partner_source = "startify"
    if ref:
        user.partner_ref = ref
    await session.flush()

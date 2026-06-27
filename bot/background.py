"""Fire-and-forget tasks that must not delay bot replies."""

from __future__ import annotations

import asyncio
import logging

from db.models import User
from services.community_broadcast import send_community_invite_to_user

logger = logging.getLogger(__name__)


def schedule_community_invite(user: User) -> None:
    async def _run() -> None:
        try:
            await send_community_invite_to_user(user)
        except Exception as exc:
            logger.debug("Background community invite failed user=%s: %s", user.id, exc)

    asyncio.create_task(_run())

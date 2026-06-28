"""Fire-and-forget tasks that must not delay bot replies."""

from __future__ import annotations

import asyncio
import logging

from db.models import User
from db.session import open_db_session
from services.community_broadcast import send_community_invite_to_user

logger = logging.getLogger(__name__)


def schedule_community_invite(user: User) -> None:
    async def _run() -> None:
        try:
            await send_community_invite_to_user(user)
        except Exception as exc:
            logger.debug("Background community invite failed user=%s: %s", user.id, exc)

    asyncio.create_task(_run())


def schedule_interest_llm_refine(user_id: int, interest_query: str) -> None:
    """LLM-категории в фоне — ответ пользователю не ждёт Groq."""

    async def _run() -> None:
        try:
            from services.interest_admin_review import save_user_interest_profile

            async with open_db_session() as session:
                await save_user_interest_profile(
                    user_id,
                    interest_query,
                    session=session,
                    skip_llm=False,
                )
                await session.commit()
            logger.info("Background interest LLM refine done user=%s", user_id)
        except Exception as exc:
            logger.warning("Background interest LLM refine failed user=%s: %s", user_id, exc)

    asyncio.create_task(_run())

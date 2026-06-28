"""Fire-and-forget tasks that must not delay bot replies."""

from __future__ import annotations

import asyncio
import logging

from config import get_settings
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


def schedule_interest_save(user_id: int, interest_query: str) -> None:
    """Локальное сохранение профиля + LLM-категории в фоне — поиск отвечает сразу."""

    async def _run() -> None:
        try:
            from db.repositories.users import (
                MatchRepository,
                MessageRepository,
                SystemStateRepository,
                UserRepository,
            )
            from services.interest_admin_review import save_user_interest_profile

            text = interest_query.strip()
            async with open_db_session() as session:
                user = await UserRepository(session).get_by_id(user_id)
                if not user:
                    return
                if (user.interest_query or "").strip() != text:
                    await MatchRepository(session).clear_processed_for_user(user_id)
                    max_raw_id = await MessageRepository(session).get_max_raw_message_id()
                    await SystemStateRepository(session).set_llm_min_raw_id(user_id, max_raw_id)
                await save_user_interest_profile(
                    user_id,
                    text,
                    session=session,
                    skip_llm=True,
                )
                await session.commit()

            settings = get_settings()
            if (
                settings.llm_interest_categorization
                and settings.llm_user_configured
                and _needs_background_llm(text)
            ):
                async with open_db_session() as session:
                    await save_user_interest_profile(
                        user_id,
                        text,
                        session=session,
                        skip_llm=False,
                    )
                    await session.commit()
            logger.info("Background interest save done user=%s", user_id)
        except Exception as exc:
            logger.warning("Background interest save failed user=%s: %s", user_id, exc)

    asyncio.create_task(_run())


def _needs_background_llm(text: str) -> bool:
    from services.interest_profile import parse_interest_profile

    profile = parse_interest_profile(text, apply_defaults=True)
    return len(profile.types) < 2 or len(profile.all_categories()) < 2


def schedule_interest_llm_refine(user_id: int, interest_query: str) -> None:
    """Совместимость — делегирует в schedule_interest_save."""
    schedule_interest_save(user_id, interest_query)

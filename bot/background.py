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


async def run_interest_side_effects(
    user_id: int,
    interest_query: str,
    *,
    results_count: int = 0,
    profile_changed: bool = True,
    log_ai_search: bool = True,
) -> None:
    """Профиль, training и event — только после ответа пользователю."""
    from analytics.event_types import AI_SEARCH
    from db.repositories.users import (
        EventRepository,
        MatchRepository,
        MessageRepository,
        SystemStateRepository,
        UserRepository,
    )
    from services.interest_admin_review import save_user_interest_profile
    from services.training_collector import record_interest_categories

    text = interest_query.strip()
    if not text:
        return

    try:
        if profile_changed:
            async with open_db_session() as session:
                user = await UserRepository(session).get_by_id(user_id)
                if not user:
                    return
                if (user.interest_query or "").strip() != text:
                    await MatchRepository(session).clear_processed_for_user(user_id)
                    max_raw_id = await MessageRepository(session).get_max_raw_message_id()
                    await SystemStateRepository(session).set_llm_min_raw_id(user_id, max_raw_id)
                profile = await save_user_interest_profile(
                    user_id,
                    text,
                    session=session,
                    skip_llm=True,
                )
                await session.commit()

            await record_interest_categories(
                user_id=user_id,
                interest_query=text,
                categories=profile.all_categories(),
                source="local",
            )

            settings = get_settings()
            if (
                settings.llm_interest_categorization
                and settings.llm_user_configured
                and _needs_background_llm(text)
            ):
                async with open_db_session() as session:
                    profile = await save_user_interest_profile(
                        user_id,
                        text,
                        session=session,
                        skip_llm=False,
                    )
                    await session.commit()
                await record_interest_categories(
                    user_id=user_id,
                    interest_query=text,
                    categories=profile.all_categories(),
                    source="llm",
                )

        if log_ai_search:
            async with open_db_session() as session:
                await EventRepository(session).log(
                    AI_SEARCH,
                    user_id=user_id,
                    metadata={"saved": profile_changed, "results": results_count},
                )
                await session.commit()

        logger.info("Interest side effects done user=%s changed=%s", user_id, profile_changed)
    except Exception as exc:
        logger.warning("Interest side effects failed user=%s: %s", user_id, exc)


def schedule_interest_side_effects(
    user_id: int,
    interest_query: str,
    *,
    results_count: int = 0,
    profile_changed: bool = True,
    log_ai_search: bool = True,
) -> None:
    asyncio.create_task(
        run_interest_side_effects(
            user_id,
            interest_query,
            results_count=results_count,
            profile_changed=profile_changed,
            log_ai_search=log_ai_search,
        )
    )


def schedule_interest_save(user_id: int, interest_query: str) -> None:
    schedule_interest_side_effects(user_id, interest_query, profile_changed=True, log_ai_search=False)


def schedule_interest_llm_refine(user_id: int, interest_query: str) -> None:
    schedule_interest_save(user_id, interest_query)


def _needs_background_llm(text: str) -> bool:
    from services.interest_profile import parse_interest_profile

    profile = parse_interest_profile(text, apply_defaults=True)
    return len(profile.types) < 2 or len(profile.all_categories()) < 2

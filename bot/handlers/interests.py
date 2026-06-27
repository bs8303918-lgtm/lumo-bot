import asyncio

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import interest_browse_keyboard, main_menu_keyboard
from bot.states import SetInterestStates
from bot.telegram_resilience import safe_answer
from bot.texts import (
    SET_INTEREST_PROMPT,
    SET_INTEREST_TOO_SHORT,
    get_interest_updated_message,
    get_no_posts_yet_onboarding,
    get_onboarding_after_interest,
    get_searching_instant,
)
from config import get_settings
from analytics.event_types import (
    INTEREST_SET,
    INTEREST_TOO_SHORT,
    ONBOARDING_CARDS,
    ONBOARDING_EMPTY_CATALOG,
    ONBOARDING_NO_MATCH,
    SET_INTEREST_STARTED,
)
from db.repositories.opportunity_catalog import OpportunityCatalogRepository
from db.repositories.users import MatchRepository, MessageRepository, SystemStateRepository, UserRepository
from services.analytics import track
from services.notification_service import NotificationService
from services.opportunity_catalog import OpportunityCatalogService
from bot.background import schedule_community_invite

router = Router()

INTEREST_MIN_LENGTH = 25


@router.message(Command("set_interest"))
async def cmd_set_interest(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(message.from_user.id, message.from_user.username)
    await track(
        session,
        SET_INTEREST_STARTED,
        user_id=user.id,
        username=message.from_user.username,
        telegram_id=message.from_user.id,
    )
    await state.set_state(SetInterestStates.waiting_for_interest)
    await safe_answer(message, SET_INTEREST_PROMPT, parse_mode="HTML", reply_markup=main_menu_keyboard())


@router.message(StateFilter(SetInterestStates.waiting_for_interest))
async def process_interest(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(message.from_user.id, message.from_user.username)

    if not message.text or len(message.text.strip()) < INTEREST_MIN_LENGTH:
        await track(
            session,
            INTEREST_TOO_SHORT,
            user_id=user.id,
            metadata={"len": len((message.text or "").strip())},
            username=message.from_user.username,
            telegram_id=message.from_user.id,
        )
        await safe_answer(message, SET_INTEREST_TOO_SHORT, reply_markup=main_menu_keyboard())
        return

    settings = get_settings()
    match_repo = MatchRepository(session)
    catalog_repo = OpportunityCatalogRepository(session)
    was_first_interest = not user.interest_query
    await match_repo.clear_processed_for_user(user.id)
    msg_repo = MessageRepository(session)
    state_repo = SystemStateRepository(session)
    max_raw_id = await msg_repo.get_max_raw_message_id()

    interest_text = message.text.strip()
    # Release middleware transaction before LLM + nested user update (SQLite lock).
    await session.commit()

    from services.interest_admin_review import save_user_interest_profile

    profile = await save_user_interest_profile(
        user.id,
        interest_text,
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )
    await track(
        session,
        INTEREST_SET,
        user_id=user.id,
        metadata={
            "first": was_first_interest,
            "text_preview": interest_text[:120],
            "categories": profile.all_categories(),
        },
        username=message.from_user.username,
        telegram_id=message.from_user.id,
        live=was_first_interest,
    )

    if was_first_interest:
        await state_repo.set_llm_min_raw_id(user.id, max_raw_id)
    else:
        await state_repo.set_llm_min_raw_id(user.id, max_raw_id)

    catalog_count = await catalog_repo.count_active_for_user(user.id)
    await session.commit()
    await state.clear()

    if catalog_count == 0:
        await track(
            session,
            ONBOARDING_EMPTY_CATALOG,
            user_id=user.id,
            username=message.from_user.username,
            telegram_id=message.from_user.id,
            live=was_first_interest,
        )
        await safe_answer(message, get_no_posts_yet_onboarding(), reply_markup=main_menu_keyboard())
        if was_first_interest:
            schedule_community_invite(user)
        return

    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    search_msg = await safe_answer(message, get_searching_instant(), reply_markup=main_menu_keyboard())

    await asyncio.sleep(0.35)
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    catalog_service = OpportunityCatalogService(NotificationService())
    digest_cap = settings.notification_digest_max_flush
    raw_max = settings.llm_onboarding_max_pairs if was_first_interest else settings.llm_max_pairs_per_cycle
    max_pairs = min(raw_max, digest_cap)

    sent = 0
    try:
        sent, _ = await catalog_service.instant_match_for_user(
            user.id,
            message.from_user.id,
            interest_text,
            max_cards=max_pairs,
            force=was_first_interest,
        )
    except Exception:
        pass

    try:
        await search_msg.delete()
    except Exception:
        pass

    if was_first_interest:
        if sent > 0:
            await track(
                session,
                ONBOARDING_CARDS,
                user_id=user.id,
                metadata={"sent": sent},
                username=message.from_user.username,
                telegram_id=message.from_user.id,
                live=True,
            )
        else:
            await track(
                session,
                ONBOARDING_NO_MATCH,
                user_id=user.id,
                metadata={"catalog_count": catalog_count},
                username=message.from_user.username,
                telegram_id=message.from_user.id,
                live=True,
            )

    category_counts = await catalog_repo.count_active_by_type_for_user(user.id) if sent == 0 else None
    browse_kb = (
        interest_browse_keyboard(profile.all_categories(), category_counts or {})
        if sent == 0
        else None
    )
    reply_markup = browse_kb or main_menu_keyboard()

    if was_first_interest:
        await safe_answer(
            message,
            get_onboarding_after_interest(
                sent,
                category_counts=category_counts,
                profile_categories=profile.all_categories(),
            ),
            reply_markup=reply_markup,
        )
        schedule_community_invite(user)
    else:
        await safe_answer(
            message,
            get_interest_updated_message(
                sent,
                category_counts=category_counts,
                profile_categories=profile.all_categories(),
            ),
            reply_markup=reply_markup,
        )

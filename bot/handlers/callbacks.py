from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.event_types import BROWSE_CATEGORY_CLICK, BUTTON_APPLY_CLICK, BUTTON_DETAILS_CLICK
from bot.callback_utils import safe_callback_answer
from bot.texts import format_browse_category_message
from db.repositories.opportunity_catalog import OpportunityCatalogRepository
from db.repositories.users import MatchRepository, UserRepository
from services.analytics import track
from services.interest_matcher import is_domain_category

router = Router()


@router.callback_query(F.data.startswith("details:"))
async def on_details_click(callback: CallbackQuery, session: AsyncSession) -> None:
    match_id = int(callback.data.split(":")[1])
    user_repo = UserRepository(session)
    match_repo = MatchRepository(session)
    user, _ = await user_repo.get_or_create(callback.from_user.id, callback.from_user.username)
    match = await match_repo.get_sent_match(match_id)
    await safe_callback_answer(callback)
    await track(session, BUTTON_DETAILS_CLICK, user_id=user.id, related_id=match_id)
    await session.commit()
    if match:
        await callback.message.answer(f"🔗 Источник: {match.message_link}")


@router.callback_query(F.data.startswith("apply:"))
async def on_apply_click(callback: CallbackQuery, session: AsyncSession) -> None:
    match_id = int(callback.data.split(":")[1])
    user_repo = UserRepository(session)
    match_repo = MatchRepository(session)
    user, _ = await user_repo.get_or_create(callback.from_user.id, callback.from_user.username)
    match = await match_repo.get_sent_match(match_id)
    await safe_callback_answer(callback)
    await track(session, BUTTON_APPLY_CLICK, user_id=user.id, related_id=match_id)
    await session.commit()
    if match and match.application_url:
        await callback.message.answer(f"🔗 Подать заявку: {match.application_url}")


@router.callback_query(F.data.startswith("browse:"))
async def on_browse_category(callback: CallbackQuery, session: AsyncSession) -> None:
    category = callback.data.split(":", 1)[1]
    await safe_callback_answer(callback)
    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(callback.from_user.id, callback.from_user.username)
    await track(
        session,
        BROWSE_CATEGORY_CLICK,
        user_id=user.id,
        metadata={"category": category},
        username=callback.from_user.username,
        telegram_id=callback.from_user.id,
    )
    repo = OpportunityCatalogRepository(session)
    if is_domain_category(category):
        items = await repo.get_active_for_domain(user.id, category, limit=3)
    else:
        items = await repo.get_active_for_user(user.id, [category], limit=3)
    await session.commit()
    if not items:
        await callback.message.answer("В этой категории пока нет активных записей.")
        return
    await callback.message.answer(
        format_browse_category_message(category, items),
        disable_web_page_preview=True,
    )

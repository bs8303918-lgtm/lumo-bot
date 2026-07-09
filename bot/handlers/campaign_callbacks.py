from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.event_types import CAMPAIGN_APPLY_CLICK, CAMPAIGN_TELEGRAM_CLICK
from bot.callback_utils import safe_callback_answer
from db.repositories.users import UserRepository
from services.analytics import track
from services.promo_campaign import load_campaign
from services.url_utils import safe_button_url

router = Router()


@router.callback_query(F.data.startswith("camp:"))
async def on_campaign_click(callback: CallbackQuery, session: AsyncSession) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await safe_callback_answer(callback, "Ошибка кнопки", show_alert=True)
        return

    _prefix, slug, action = parts
    if action not in {"apply", "telegram", "link"}:
        await safe_callback_answer(callback, "Неизвестное действие", show_alert=True)
        return

    try:
        campaign = load_campaign(slug)
    except FileNotFoundError:
        await safe_callback_answer(callback, "Кампания не найдена", show_alert=True)
        return

    if action == "apply":
        url = safe_button_url(campaign.apply_url)
        event_type = CAMPAIGN_APPLY_CLICK
    else:
        url = safe_button_url(campaign.telegram_url or campaign.info_url)
        event_type = CAMPAIGN_TELEGRAM_CLICK

    if not url:
        await safe_callback_answer(callback, "Ссылка недоступна", show_alert=True)
        return

    await safe_callback_answer(callback, url=url)

    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(callback.from_user.id, callback.from_user.username)
    await track(
        session,
        event_type,
        user_id=user.id,
        metadata={"campaign": slug, "url": url},
        username=callback.from_user.username,
        telegram_id=callback.from_user.id,
    )
    await session.commit()

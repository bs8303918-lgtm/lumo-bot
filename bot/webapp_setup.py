import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import MenuButtonWebApp, WebAppInfo

from config import get_settings

logger = logging.getLogger(__name__)


def _menu_webapp_url() -> str:
    return get_settings().telegram_webapp_base_url


async def setup_telegram_webapp(bot: Bot) -> None:
    """Default blue Open button (left of input) for all private chats."""
    url = _menu_webapp_url()
    if not url:
        logger.warning(
            "Mini App URL not set — Open button disabled. Set TELEGRAM_WEBAPP_URL or PUBLIC_BASE_URL"
        )
        return

    menu = MenuButtonWebApp(
        text=get_settings().mini_app_menu_text[:16] or "Open",
        web_app=WebAppInfo(url=url),
    )
    try:
        await bot.set_chat_menu_button(menu_button=menu)
        logger.info("Menu button Open -> %s", url)
    except TelegramBadRequest as exc:
        logger.error(
            "Menu button URL rejected (%s). BotFather → bot → Configure Mini App → "
            "add domain from URL (e.g. lumo-bot.vercel.app). URL was: %s",
            exc,
            url,
        )


async def sync_user_menu_button(bot: Bot, chat_id: int) -> None:
    """Push the current Mini App URL for this chat (overrides stale cached URLs)."""
    url = _menu_webapp_url()
    if not url:
        return
    try:
        await bot.set_chat_menu_button(
            chat_id=chat_id,
            menu_button=MenuButtonWebApp(
                text=get_settings().mini_app_menu_text[:16] or "Open",
                web_app=WebAppInfo(url=url),
            ),
        )
    except TelegramBadRequest as exc:
        logger.warning("Menu button for chat %s rejected: %s", chat_id, exc)

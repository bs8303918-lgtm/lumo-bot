import logging

from aiogram import Bot
from aiogram.types import MenuButtonWebApp, WebAppInfo

from config import get_settings

logger = logging.getLogger(__name__)


async def setup_telegram_webapp(bot: Bot) -> None:
    """Default blue Open button (left of input) for all private chats."""
    settings = get_settings()
    url = settings.resolved_webapp_url
    if not url:
        logger.warning(
            "Mini App URL not set — Open button disabled. Set PUBLIC_BASE_URL in .env"
        )
        return

    menu = MenuButtonWebApp(
        text=settings.mini_app_menu_text[:16] or "Open",
        web_app=WebAppInfo(url=url),
    )
    await bot.set_chat_menu_button(menu_button=menu)
    logger.info("Menu button Open -> %s", url)


async def sync_user_menu_button(bot: Bot, chat_id: int) -> None:
    """Push the current Mini App URL for this chat (overrides stale cached URLs)."""
    settings = get_settings()
    url = settings.resolved_webapp_url
    if not url:
        return
    await bot.set_chat_menu_button(
        chat_id=chat_id,
        menu_button=MenuButtonWebApp(
            text=settings.mini_app_menu_text[:16] or "Open",
            web_app=WebAppInfo(url=url),
        ),
    )

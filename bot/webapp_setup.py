"""Telegram Mini App menu button — run once, not on every /start."""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import MenuButtonWebApp, WebAppInfo

from config import get_settings

logger = logging.getLogger(__name__)

_menu_configured = False
_synced_chat_ids: set[int] = set()


def _menu_webapp_url() -> str:
    return get_settings().telegram_webapp_base_url


async def setup_telegram_webapp(bot: Bot, *, force: bool = False) -> None:
    """Default blue Open button (left of input). Called once at bot startup."""
    global _menu_configured
    if _menu_configured and not force:
        return

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
        _menu_configured = True
        logger.info("Menu button Open -> %s", url)
    except TelegramBadRequest as exc:
        logger.error(
            "Menu button URL rejected (%s). BotFather → bot → Configure Mini App → "
            "add domain from URL (e.g. lumo-bot.vercel.app). URL was: %s",
            exc,
            url,
        )


async def sync_user_menu_button(bot: Bot, chat_id: int, *, force: bool = False) -> None:
    """Per-chat menu URL refresh — cached after first successful sync."""
    if chat_id in _synced_chat_ids and not force:
        return

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
        _synced_chat_ids.add(chat_id)
    except TelegramBadRequest as exc:
        logger.warning("Menu button for chat %s rejected: %s", chat_id, exc)


def schedule_menu_sync(bot: Bot, chat_id: int, *, force: bool = False) -> None:
    """Fire-and-forget — must not block handler replies."""

    async def _run() -> None:
        try:
            await sync_user_menu_button(bot, chat_id, force=force)
        except Exception as exc:
            logger.debug("Background menu sync failed chat=%s: %s", chat_id, exc)

    asyncio.create_task(_run())


def reset_menu_cache() -> None:
    """After /sync_webapp — force re-push to all chats."""
    global _menu_configured
    _menu_configured = False
    _synced_chat_ids.clear()

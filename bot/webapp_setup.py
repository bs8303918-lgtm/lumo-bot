"""Telegram Mini App menu button — run once, not on every /start."""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import MenuButtonWebApp, WebAppInfo

from config import get_settings
from services.url_utils import safe_webapp_url

logger = logging.getLogger(__name__)

_menu_configured = False
_synced_chat_ids: set[int] = set()


def _menu_webapp_url() -> str:
    return safe_webapp_url(get_settings().telegram_webapp_base_url)


async def setup_telegram_webapp(bot: Bot, *, force: bool = False) -> None:
    """Default blue Open button (left of input). Called once at bot startup."""
    global _menu_configured
    if _menu_configured and not force:
        return

    url = _menu_webapp_url()
    if not url:
        logger.warning(
            "Mini App URL not set or invalid — Open button disabled. "
            "Set TELEGRAM_WEBAPP_URL to your Vercel HTTPS URL (not Railway /app)."
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


async def resync_menu_button_for_all_users(bot: Bot) -> dict[str, int]:
    """Overwrite every user's per-chat Menu Button with the current URL.

    Telegram persists a per-chat override forever once set (e.g. from an old
    dev/testing domain) — the global default button never overrides it, so a
    stale chat only self-heals once that user sends /start again. This pushes
    the current URL to everyone directly instead of waiting for that.
    """
    from db.base import async_session_factory
    from db.repositories.users import UserRepository
    from services.notification_service import is_unreachable_user_error

    url = _menu_webapp_url()
    stats = {"target": 0, "synced": 0, "unreachable": 0, "failed": 0}
    if not url:
        return stats

    menu = MenuButtonWebApp(
        text=get_settings().mini_app_menu_text[:16] or "Open",
        web_app=WebAppInfo(url=url),
    )

    async with async_session_factory() as session:
        users = await UserRepository(session).list_all()
    stats["target"] = len(users)

    for user in users:
        try:
            await bot.set_chat_menu_button(chat_id=user.telegram_id, menu_button=menu)
            _synced_chat_ids.add(user.telegram_id)
            stats["synced"] += 1
        except TelegramBadRequest as exc:
            if is_unreachable_user_error(exc):
                stats["unreachable"] += 1
            else:
                logger.warning("Menu resync failed chat=%s: %s", user.telegram_id, exc)
                stats["failed"] += 1
        except Exception as exc:
            logger.warning("Menu resync failed chat=%s: %s", user.telegram_id, exc)
            stats["failed"] += 1
        await asyncio.sleep(0.05)

    return stats

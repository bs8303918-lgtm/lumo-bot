from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession

from config import get_settings

_polling_bot: Bot | None = None
_notify_bot: Bot | None = None


def _make_session() -> AiohttpSession:
    settings = get_settings()
    return AiohttpSession(
        timeout=settings.bot_http_timeout_seconds,
        limit=50,
    )


def create_bot() -> Bot:
    """Bot для polling и ответов пользователям в хендлерах."""
    global _polling_bot
    if _polling_bot is not None:
        return _polling_bot

    settings = get_settings()
    _polling_bot = Bot(token=settings.telegram_bot_token, session=_make_session())
    return _polling_bot


def get_bot() -> Bot:
    return create_bot()


def get_notify_bot() -> Bot:
    """Отдельная сессия для фоновых рассылок — не блокирует polling."""
    global _notify_bot
    if _notify_bot is not None:
        return _notify_bot

    settings = get_settings()
    _notify_bot = Bot(token=settings.telegram_bot_token, session=_make_session())
    return _notify_bot


async def close_bot() -> None:
    global _polling_bot, _notify_bot
    for bot in (_polling_bot, _notify_bot):
        if bot is not None:
            await bot.session.close()
    _polling_bot = None
    _notify_bot = None

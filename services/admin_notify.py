import logging

from bot.instance import get_notify_bot
from config import get_settings

logger = logging.getLogger(__name__)


async def notify_admin(text: str) -> None:
    settings = get_settings()
    if not settings.telegram_admin_chat_id:
        return
    try:
        bot = get_notify_bot()
        await bot.send_message(settings.telegram_admin_chat_id, text)
    except Exception as exc:
        logger.error("Failed to notify admin: %s", exc)

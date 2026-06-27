import asyncio
import logging

from aiogram.exceptions import TelegramNetworkError
from aiogram.types import Message

logger = logging.getLogger(__name__)


async def safe_answer(message: Message, text: str, *, retries: int = 3, **kwargs):
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return await message.answer(text, **kwargs)
        except TelegramNetworkError as exc:
            last_exc = exc
            if attempt < retries - 1:
                wait = min(2.0 * (attempt + 1), 6.0)
                logger.warning(
                    "Telegram сеть: повтор ответа через %.0f сек (%d/%d)",
                    wait,
                    attempt + 1,
                    retries,
                )
                await asyncio.sleep(wait)
    logger.warning("Telegram: не удалось отправить ответ после %d попыток", retries)
    if last_exc:
        raise last_exc
    return None

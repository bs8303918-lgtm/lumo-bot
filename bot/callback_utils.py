"""Безопасный ответ на inline-кнопки — Telegram требует answer за ~10 сек."""

from __future__ import annotations

import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)

_STALE_MARKERS = (
    "query is too old",
    "response timeout expired",
    "query id is invalid",
)


def is_stale_callback_error(exc: Exception) -> bool:
    if not isinstance(exc, TelegramBadRequest):
        return False
    text = str(exc).lower()
    return any(marker in text for marker in _STALE_MARKERS)


async def safe_callback_answer(
    callback: CallbackQuery,
    text: str | None = None,
    *,
    show_alert: bool = False,
    url: str | None = None,
) -> bool:
    """Ответить на callback. False — кнопка протухла (старый пост)."""
    try:
        await callback.answer(text=text, show_alert=show_alert, url=url)
        return True
    except TelegramBadRequest as exc:
        if is_stale_callback_error(exc):
            logger.debug(
                "Stale callback ignored data=%s user=%s",
                callback.data,
                callback.from_user.id if callback.from_user else None,
            )
            return False
        if "url_invalid" in str(exc).lower():
            logger.warning("Invalid callback URL data=%s: %s", callback.data, exc)
            await callback.answer("Ссылка недоступна", show_alert=True)
            return False
        raise

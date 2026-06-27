import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError

from bot.instance import get_notify_bot
from config import get_settings
from db.base import async_session_factory
from db.repositories.users import SystemStateRepository
from services.match_digest import PendingMatch, format_digest_message, get_digest_buffer

logger = logging.getLogger(__name__)


def format_match_card(data: dict) -> str:
    requirements = ""
    if data.get("requirements"):
        requirements = f"\n\n📋 Требования: {data['requirements']}"

    tags = data.get("tags") or []
    if tags:
        type_line = ", ".join(tags)
    else:
        type_line = data.get("type", "—")

    return (
        "🎯 Найдено по твоему запросу\n\n"
        f"📌 {data['title']}\n"
        f"🏷 Теги: {type_line}\n"
        f"📅 Дедлайн: {data['deadline']}\n\n"
        f"{data['description']}"
        f"{requirements}\n\n"
        f"📍 Источник: {data['source_channel_name']}\n"
        f"🔗 {data['message_link']}"
    )


def is_unreachable_user_error(exc: Exception) -> bool:
    if isinstance(exc, TelegramForbiddenError):
        return True
    if isinstance(exc, TelegramBadRequest):
        msg = str(exc).lower()
        return any(
            phrase in msg
            for phrase in (
                "bot was blocked by the user",
                "user is deactivated",
                "chat not found",
            )
        )
    return False


def _digest_state_key(user_id: int) -> str:
    return f"digest_last_sent:{user_id}"


async def digest_cooldown_active(user_id: int) -> bool:
    settings = get_settings()
    hours = settings.digest_cooldown_hours
    if hours <= 0:
        return False
    async with async_session_factory() as session:
        raw = await SystemStateRepository(session).get(_digest_state_key(user_id))
    if not raw:
        return False
    try:
        last = datetime.fromisoformat(raw)
    except ValueError:
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last < timedelta(hours=hours)


async def mark_digest_sent(user_id: int) -> None:
    async with async_session_factory() as session:
        await SystemStateRepository(session).set(
            _digest_state_key(user_id),
            datetime.now(timezone.utc).isoformat(),
        )
        await session.commit()


class NotificationService:
    async def enqueue_match(
        self,
        user_id: int,
        telegram_id: int,
        match_id: int,
        card_data: dict,
        *,
        flush_remaining: bool = False,
        auto_flush: bool = True,
    ) -> bool:
        """Добавить в очередь. auto_flush=False — только копим до явного flush."""
        buffer = get_digest_buffer()
        buffer.add(user_id, telegram_id, match_id, card_data)
        if auto_flush:
            await buffer.flush_ready(user_id, self)
        if flush_remaining:
            settings = get_settings()
            await buffer.flush_remaining(
                user_id,
                self,
                max_items=settings.notification_digest_max_flush,
            )
        return True

    async def flush_user_digest(
        self,
        user_id: int,
        *,
        flush_remaining: bool = False,
        max_items: int | None = None,
    ) -> int:
        buffer = get_digest_buffer()
        sent = await buffer.flush_ready(user_id, self)
        if flush_remaining:
            settings = get_settings()
            cap = max_items if max_items is not None else settings.notification_digest_max_flush
            sent += await buffer.flush_remaining(user_id, self, max_items=cap)
        return sent

    async def send_digest(
        self,
        telegram_id: int,
        items: list[PendingMatch],
        *,
        user_id: int | None = None,
    ) -> bool:
        if not items:
            return True
        bot = get_notify_bot()
        text = format_digest_message([item.card_data for item in items])

        for attempt in range(3):
            try:
                await bot.send_message(
                    telegram_id,
                    text,
                    disable_web_page_preview=True,
                )
                logger.info(
                    "Telegram: отправлена подборка (%d) user=%s",
                    len(items),
                    telegram_id,
                )
                if user_id is not None:
                    await mark_digest_sent(user_id)
                return True
            except TelegramNetworkError:
                if attempt >= 2:
                    logger.warning("Telegram: не удалось отправить подборку user=%s", telegram_id)
                    raise
                await asyncio.sleep(2.0 * (attempt + 1))
            except Exception as exc:
                if is_unreachable_user_error(exc):
                    logger.info("Telegram: user %s недоступен — %s", telegram_id, exc)
                    return False
                raise
        return False

    async def send_match_card(self, telegram_id: int, match_id: int, card_data: dict) -> bool:
        """Legacy: одна карточка — используй enqueue_match."""
        return await self.send_digest(telegram_id, [PendingMatch(match_id, card_data)])

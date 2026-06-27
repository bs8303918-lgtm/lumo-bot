from aiogram import Dispatcher
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.fsm.storage.memory import MemoryStorage
import logging

from analytics.event_types import HANDLER_ERROR
from bot.handlers import router as handlers_router
from bot.middlewares import DbSessionMiddleware
from db.base import async_session_factory
from db.repositories.users import EventRepository, UserRepository
from services.admin_notify import notify_admin
from services.analytics import track
from bot.callback_utils import is_stale_callback_error
from services.notification_service import is_unreachable_user_error

logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(handlers_router)

    @dp.errors()
    async def on_handler_error(event):
        exc = event.exception
        if isinstance(exc, TelegramNetworkError):
            logger.warning("Telegram сеть: update не обработан — %s", exc)
            return True

        if is_stale_callback_error(exc):
            logger.debug("Stale callback query ignored: %s", exc)
            return True

        update = event.update
        user = None
        if update.message and update.message.from_user:
            user = update.message.from_user
        elif update.callback_query and update.callback_query.from_user:
            user = update.callback_query.from_user

        if is_unreachable_user_error(exc):
            logger.info("Пользователь недоступен (бот заблокирован или чат удалён): %s", exc)
            if user:
                try:
                    async with async_session_factory() as session:
                        db_user, _ = await UserRepository(session).get_or_create(
                            user.id, user.username
                        )
                        await UserRepository(session).set_notifications_enabled(db_user.id, False)
                        await session.commit()
                except Exception:
                    logger.exception("Failed to disable notifications for blocked user")
            return True

        err_text = f"{type(exc).__name__}: {exc}"[:300]
        logger.exception("Handler error: %s", err_text)

        try:
            async with async_session_factory() as session:
                user_id = None
                if user:
                    db_user, _ = await UserRepository(session).get_or_create(user.id, user.username)
                    user_id = db_user.id
                await track(
                    session,
                    HANDLER_ERROR,
                    user_id=user_id,
                    metadata={"error": err_text},
                    username=user.username if user else None,
                    telegram_id=user.id if user else None,
                    live=True,
                )
                await session.commit()
        except Exception:
            logger.exception("Failed to log handler error")

        await notify_admin(f"🚨 Ошибка бота\n{err_text}")
        return False

    return dp

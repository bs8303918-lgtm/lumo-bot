from aiogram.types import Message

from bot.keyboards import main_menu_keyboard, webapp_open_inline
from bot.texts import WELCOME_MESSAGE_EFFECT_ID, get_welcome_text
from bot.webapp_setup import sync_user_menu_button, setup_telegram_webapp
from db.base import async_session_factory
from db.repositories.users import UserRepository
from services.community_broadcast import send_community_invite_to_user
from services.notification_service import is_unreachable_user_error


async def send_welcome(message: Message) -> None:
    try:
        await setup_telegram_webapp(message.bot)
        await sync_user_menu_button(message.bot, message.chat.id)
    except Exception as exc:
        if is_unreachable_user_error(exc):
            return
        raise

    kwargs = {
        "text": get_welcome_text(),
        "reply_markup": main_menu_keyboard(),
        "message_effect_id": WELCOME_MESSAGE_EFFECT_ID,
    }
    try:
        await message.answer(**kwargs)
    except Exception as exc:
        if is_unreachable_user_error(exc):
            return
        await message.answer(get_welcome_text(), reply_markup=main_menu_keyboard())

    inline = webapp_open_inline()
    if inline:
        await message.answer(
            "📱 Открой Mini App кнопкой ниже (не старую вкладку с ошибкой):",
            reply_markup=inline,
        )

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(message.from_user.id, message.from_user.username)
    await send_community_invite_to_user(user)

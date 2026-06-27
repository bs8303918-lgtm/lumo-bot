from aiogram.types import Message

from bot.background import schedule_community_invite
from bot.keyboards import main_menu_keyboard, webapp_open_inline
from bot.texts import WELCOME_MESSAGE_EFFECT_ID, get_welcome_text
from bot.webapp_setup import schedule_menu_sync
from services.notification_service import is_unreachable_user_error


async def send_welcome(message: Message, *, user=None) -> None:
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

    schedule_menu_sync(message.bot, message.chat.id)
    if user is not None:
        schedule_community_invite(user)

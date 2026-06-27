from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.keyboards import main_menu_keyboard
from config import get_settings

router = Router()


@router.message(Command("bug"))
async def cmd_bug(message: Message) -> None:
    contact = get_settings().support_contact
    await message.answer(
        f"🐛 Нашёл баг или что-то работает не так?\n\n"
        f"Напиши {contact} в Telegram:\n"
        "• что делал(а)\n"
        "• что ожидал(а)\n"
        "• скрин или текст ошибки, если есть\n\n"
        "Спасибо, это помогает улучшать Lumo 🙌",
        reply_markup=main_menu_keyboard(),
    )

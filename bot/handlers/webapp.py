from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards import main_menu_keyboard, webapp_open_inline
from bot.webapp_setup import schedule_menu_sync
from config import get_settings

router = Router()


@router.message(Command("app"))
async def cmd_app(message: Message) -> None:
    settings = get_settings()
    url = settings.resolved_webapp_url

    if url:
        inline = webapp_open_inline()
        await message.answer(
            "📱 Mini App\n\n"
            "1. Нажми <b>📱 Open Mini App</b> ниже (новое сообщение — свежий URL)\n"
            "2. Не открывай старую вкладку Mini App — закрой крестиком\n"
            "3. Синяя <b>Open</b> слева обновится после /start\n\n"
            f"URL: <code>{url}</code>",
            parse_mode="HTML",
            reply_markup=inline or main_menu_keyboard(),
        )
        if inline:
            await message.answer("Меню:", reply_markup=main_menu_keyboard())
        schedule_menu_sync(message.bot, message.chat.id, force=True)
        return

    await message.answer(
        "📱 Mini App не настроен.\n\n"
        "1. Запусти бота: <code>python main.py</code>\n"
        "2. Туннель: <code>.\\scripts\\setup_tunnel.ps1</code>\n"
        "3. В .env: <code>PUBLIC_BASE_URL=https://....trycloudflare.com</code>\n"
        "4. Перезапусти бота",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("link"))
async def cmd_link(message: Message) -> None:
    """Plain HTTPS link — bypasses Telegram WebView cache of old tunnel URLs."""
    settings = get_settings()
    url = settings.resolved_webapp_url
    if not url:
        await message.answer("URL не задан. Добавь PUBLIC_BASE_URL в .env и перезапусти бота.")
        return
    plain = url.split("?", 1)[0]
    await message.answer(
        "Если видишь <code>ser-penalties...</code> — это кэш Telegram.\n\n"
        "1. Закрой Mini App крестиком\n"
        "2. Нажми кнопку ниже\n"
        "3. В @BotFather → /myapps → Edit link → новый URL\n\n"
        f"<code>{plain}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔗 Открыть Lumo", url=plain)]]
        ),
    )
    schedule_menu_sync(message.bot, message.chat.id, force=True)

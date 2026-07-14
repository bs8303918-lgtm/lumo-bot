from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards import main_menu_keyboard, webapp_open_inline
from bot.webapp_setup import schedule_menu_sync
from config import get_settings
from services.url_utils import safe_button_url

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
        "Prod: задай <code>TELEGRAM_WEBAPP_URL=https://lumo-bot.vercel.app</code>\n"
        "и <code>PUBLIC_BASE_URL</code> = Railway API URL, затем перезапусти бота.\n\n"
        "Локально: туннель + <code>PUBLIC_BASE_URL</code> HTTPS, либо сразу Vercel URL.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("link"))
async def cmd_link(message: Message) -> None:
    """Plain HTTPS link — bypasses Telegram WebView cache of old tunnel URLs."""
    settings = get_settings()
    url = settings.resolved_webapp_url
    if not url:
        await message.answer(
            "URL не задан. Добавь TELEGRAM_WEBAPP_URL (Vercel) в .env и перезапусти бота."
        )
        return
    plain = safe_button_url(url.split("?", 1)[0])
    if not plain:
        await message.answer(
            "URL Mini App некорректен для Telegram.\n"
            "Задай TELEGRAM_WEBAPP_URL (Vercel HTTPS), не Railway /app."
        )
        return
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

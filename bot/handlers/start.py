from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.background import schedule_community_invite
from bot.keyboards import community_join_inline, main_menu_keyboard, subscription_upsell_keyboard, webapp_open_inline
from bot.texts import get_community_invite_text, get_help_text, get_startify_trial_welcome
from bot.webapp_setup import schedule_menu_sync
from bot.welcome import send_welcome
from config import get_settings
from db.repositories.channels import ChannelRepository
from db.repositories.users import SystemStateRepository, UserRepository
from analytics.event_types import RETURNING_START, USER_REGISTERED, WELCOME_SHOWN
from services.analytics import track
from services.partner_attribution import apply_start_payload

router = Router()


def _format_ago(iso_str: str | None, *, never: str = "никогда") -> str:
    if not iso_str or iso_str == never:
        return never
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        mins = int(delta.total_seconds() / 60)
        if mins < 1:
            return "только что"
        if mins < 60:
            return f"{mins} мин назад"
        hours = mins // 60
        if hours < 24:
            return f"{hours} ч назад"
        return f"{hours // 24} д назад"
    except ValueError:
        return iso_str


@router.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    await message.answer(
        f"✅ Lumo онлайн\n🕐 {now}\n\n"
        "Подробнее: /status\n"
        "Проверить LLM: /test",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("whoami"))
async def cmd_whoami(message: Message) -> None:
    settings = get_settings()
    uid = message.from_user.id
    is_admin = settings.is_admin(uid)
    await message.answer(
        f"🆔 Твой Telegram ID: <code>{uid}</code>\n"
        f"Admin: {'✅ да' if is_admin else '❌ нет'}\n\n"
        "Если Admin «нет», но должен быть — проверь "
        "<code>TELEGRAM_ADMIN_CHAT_ID</code> в .env и перезапусти бота.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("status"))
async def cmd_status(message: Message, session: AsyncSession) -> None:
    settings = get_settings()
    state_repo = SystemStateRepository(session)
    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(message.from_user.id, message.from_user.username)

    last_monitor = await state_repo.get("last_monitor_success_at")
    last_llm = await state_repo.get("llm_processor_last_run_at")
    monitor_hours = max(1, settings.monitor_interval_minutes // 60)
    llm_minutes = max(1, settings.llm_processor_interval_seconds // 60)

    if monitor_hours >= 24:
        monitor_schedule = "раз в сутки"
    else:
        monitor_schedule = f"каждые {monitor_hours} ч"

    await message.answer(
        "📡 Статус Lumo\n\n"
        f"Бот: ✅ онлайн\n"
        f"Профиль: {'✅ задан' if user.interest_query else '❌ не задан — /set_interest'}\n"
        f"Последний скан каналов: {_format_ago(last_monitor)}\n"
        f"Последний анализ постов: {_format_ago(last_llm)}\n\n"
        f"Расписание: каналы {monitor_schedule}, "
        f"анализ ~каждые {llm_minutes} мин.\n\n"
        "Быстрая проверка: /ping\n"
        "Проверить умный отбор: /test",
        reply_markup=main_menu_keyboard(),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    channel_repo = ChannelRepository(session)

    user, created = await user_repo.get_or_create(
        message.from_user.id,
        message.from_user.username,
    )
    start_payload = None
    if message.text and " " in message.text.strip():
        start_payload = message.text.strip().split(maxsplit=1)[1]
    startify = await apply_start_payload(session, user, start_payload)
    if startify.trial_granted:
        await message.answer(
            get_startify_trial_welcome(user.tariff_expires_at),
            parse_mode="HTML",
            reply_markup=subscription_upsell_keyboard() or main_menu_keyboard(),
        )
    if created:
        await track(
            session,
            USER_REGISTERED,
            user_id=user.id,
            username=message.from_user.username,
            telegram_id=message.from_user.id,
            live=True,
        )

    channels = await channel_repo.get_user_channels(user.id)
    interest = user.interest_query

    if created or (not channels and not interest):
        await track(
            session,
            WELCOME_SHOWN,
            user_id=user.id,
            metadata={"new": created},
            username=message.from_user.username,
            telegram_id=message.from_user.id,
        )
        await send_welcome(message, user=user)
        return

    await track(
        session,
        RETURNING_START,
        user_id=user.id,
        username=message.from_user.username,
        telegram_id=message.from_user.id,
    )

    interest_text = interest or "не задан — /set_interest"
    inline = webapp_open_inline()

    await message.answer(
        f"👋 Снова привет!\n\n"
        f"🎯 Запрос: {interest_text}\n"
        f"📡 Каналов: {len(channels)}/5\n\n"
        f"ℹ️ /help · Mini App — кнопки ниже (не старую вкладку)",
        parse_mode="HTML",
        reply_markup=inline or main_menu_keyboard(),
    )
    if inline:
        await message.answer("Меню:", reply_markup=main_menu_keyboard())

    schedule_menu_sync(message.bot, message.chat.id)
    schedule_community_invite(user)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(get_help_text(), parse_mode="HTML", reply_markup=main_menu_keyboard())


@router.message(Command("community"))
async def cmd_community(message: Message) -> None:
    inline = community_join_inline()
    if not inline:
        await message.answer(
            "Ссылка на сообщество пока не настроена.",
            reply_markup=main_menu_keyboard(),
        )
        return
    await message.answer(
        get_community_invite_text(),
        parse_mode="HTML",
        reply_markup=inline,
    )

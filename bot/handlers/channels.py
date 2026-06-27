from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import channel_list_keyboard
from bot.states import AddChannelStates
from config import get_settings
from db.base import async_session_factory
from db.repositories.channels import ChannelRepository
from db.repositories.users import EventRepository, UserRepository, normalize_channel_identifier
from monitor.channel_resolver import ChannelResolver
from monitor.telethon_client import require_authorized_client
from monitor.worker import MonitorWorker
from services.notification_service import NotificationService
from services.opportunity_catalog import OpportunityCatalogService

router = Router()


@router.message(Command("add_channel"))
async def cmd_add_channel(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    channel_repo = ChannelRepository(session)
    user, _ = await user_repo.get_or_create(message.from_user.id, message.from_user.username)

    count = await channel_repo.count_user_channels(user.id)
    if count >= get_settings().max_user_channels:
        await message.answer(
            f"У тебя уже {get_settings().max_user_channels} каналов — это максимум.\n"
            "Удали один через /my_channels перед добавлением нового."
        )
        return

    await state.set_state(AddChannelStates.waiting_for_channel)
    await message.answer(
        "Пришли @username публичного канала или ссылку на него.\n\n"
        "Примеры:\n"
        "• @startup_course_com\n"
        "• @uppertunity"
    )


@router.message(StateFilter(AddChannelStates.waiting_for_channel), ~F.text.startswith("/"))
async def process_channel_input(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.text:
        await message.answer("Пришли @username канала, например @startup_course_com")
        return

    user_repo = UserRepository(session)
    channel_repo = ChannelRepository(session)
    event_repo = EventRepository(session)
    user, _ = await user_repo.get_or_create(message.from_user.id, message.from_user.username)

    identifier = normalize_channel_identifier(message.text)
    if await channel_repo.user_has_channel(user.id, identifier):
        await message.answer("Этот канал уже в твоём списке.")
        await state.clear()
        return

    client = await require_authorized_client()
    if not client:
        await message.answer(
            "Сейчас мониторинг каналов не настроен (Telethon не залогинен). "
            "Попробуй позже или напиши администратору."
        )
        await state.clear()
        return

    resolver = ChannelResolver(client)
    info, error = await resolver.validate_public_channel(message.text)

    if error or not info:
        await message.answer(error or "Канал не прошёл проверку.")
        await state.clear()
        return

    await channel_repo.add_user_channel(user.id, info.identifier, info.title)
    await event_repo.log(
        "channel_added",
        user_id=user.id,
        metadata={"channel": info.identifier},
    )
    await session.commit()
    await state.clear()

    scan_note = ""
    async with async_session_factory() as scan_session:
        monitored = await ChannelRepository(scan_session).get_monitored_by_identifier(info.identifier)
        if monitored:
            await MonitorWorker().scan_channel(monitored.id)
            scan_note = "\n\n🔍 Канал просканирован."
            if user.interest_query:
                try:
                    sent, _ = await OpportunityCatalogService(
                        NotificationService()
                    ).instant_match_for_user(
                        user.id,
                        message.from_user.id,
                        user.interest_query,
                        max_cards=3,
                    )
                    if sent:
                        scan_note += f" Подобрал {sent} из каталога."
                    else:
                        scan_note += " Новые посты попадут в каталог в ближайший цикл."
                except Exception:
                    scan_note += " Каталог обновится в ближайший цикл."
            else:
                scan_note += " Задай /set_interest — тогда смогу отбирать объявления."

    await message.answer(
        f"✅ Канал @{info.identifier} добавлен!\n"
        f"Название: {info.title}\n\n"
        "Не забудь задать запрос через /set_interest, если ещё не сделал."
        f"{scan_note}"
    )


@router.message(Command("my_channels"))
async def cmd_my_channels(message: Message, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    channel_repo = ChannelRepository(session)
    user, _ = await user_repo.get_or_create(message.from_user.id, message.from_user.username)
    channels = await channel_repo.get_user_channels(user.id)

    if not channels:
        await message.answer(
            "У тебя пока нет своих каналов.\n"
            "Базовые каналы Lumo мониторятся автоматически.\n"
            "Добавить свой: /add_channel"
        )
        return

    text = f"Твои каналы ({len(channels)}/{get_settings().max_user_channels}):\n\n"
    for ch in channels:
        title = ch.channel_title or ch.channel_identifier
        text += f"• @{ch.channel_identifier} — {title}\n"

    await message.answer(text, reply_markup=channel_list_keyboard(channels))
    await message.answer("Нажми 🗑 на канал, чтобы убрать его из мониторинга.")


@router.callback_query(F.data.startswith("remove_channel:"))
async def remove_channel_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    channel_id = int(callback.data.split(":")[1])
    user_repo = UserRepository(session)
    channel_repo = ChannelRepository(session)
    event_repo = EventRepository(session)
    user, _ = await user_repo.get_or_create(callback.from_user.id, callback.from_user.username)

    removed = await channel_repo.remove_user_channel(user.id, channel_id)
    if removed:
        await event_repo.log("channel_removed", user_id=user.id, metadata={"channel": removed})
        await callback.answer("Канал удалён")
        channels = await channel_repo.get_user_channels(user.id)
        if channels:
            text = f"Твои каналы ({len(channels)}/{get_settings().max_user_channels}):\n\n"
            for ch in channels:
                title = ch.channel_title or ch.channel_identifier
                text += f"• @{ch.channel_identifier} — {title}\n"
            await callback.message.edit_text(text, reply_markup=channel_list_keyboard(channels))
        else:
            await callback.message.edit_text("Все твои каналы удалены. Базовые каналы Lumo по-прежнему мониторятся.")
    else:
        await callback.answer("Канал не найден", show_alert=True)

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.channels import cmd_add_channel
from bot.handlers.interests import cmd_set_interest
from bot.keyboards import BTN_COMMUNITY, BTN_HELP, BTN_MY_CRITERIA, BTN_TRACK_CHANNEL, community_join_inline, main_menu_keyboard
from bot.texts import get_community_invite_text, get_help_text
from db.repositories.users import UserRepository

router = Router()


@router.message(F.text == BTN_HELP)
async def menu_help(message: Message) -> None:
    await message.answer(get_help_text(), parse_mode="HTML", reply_markup=main_menu_keyboard())


@router.message(F.text == BTN_COMMUNITY)
async def menu_community(message: Message) -> None:
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


@router.message(F.text == BTN_TRACK_CHANNEL)
async def menu_track_channel(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await cmd_add_channel(message, state, session)


@router.message(F.text == BTN_MY_CRITERIA)
async def menu_my_criteria(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(message.from_user.id, message.from_user.username)

    if user.interest_query:
        await message.answer(
            f"🎯 Твои критерии:\n«{user.interest_query}»\n\n"
            "Изменить: /set_interest",
            reply_markup=main_menu_keyboard(),
        )
        return

    await cmd_set_interest(message, state, session)

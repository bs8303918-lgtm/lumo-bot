from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states import TestPostStates
from db.repositories.users import UserRepository
from llm.client import LLMClient
from llm.deadline import is_opportunity_expired
from llm.spam_filter import is_likely_spam_or_ad
from services.notification_service import format_match_card

router = Router()


@router.message(Command("test"))
async def cmd_test(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(message.from_user.id, message.from_user.username)

    if not user.interest_query:
        await message.answer("Сначала задай запрос через /set_interest — без него не с чем сравнивать.")
        return

    await state.set_state(TestPostStates.waiting_for_text)
    await message.answer(
        "Пришли текст объявления одним сообщением — проверю, пришлю ли я тебе такую карточку из канала.\n\n"
        f"Твой запрос: «{user.interest_query}»"
    )


@router.message(StateFilter(TestPostStates.waiting_for_text))
async def process_test_post(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.text or len(message.text.strip()) < 20:
        await message.answer("Пришли полный текст объявления (хотя бы пару предложений).")
        return

    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(message.from_user.id, message.from_user.username)
    await state.clear()

    llm = LLMClient()
    if not llm.settings.llm_configured:
        await message.answer("LLM не настроен — проверь API-ключ в .env.")
        return

    if not await llm.is_available():
        await message.answer("LLM сейчас недоступен (ключ или квота). Попробуй позже.")
        return

    text = message.text.strip()
    is_spam, _ = is_likely_spam_or_ad(text)
    if is_spam:
        await message.answer(
            "❌ Это похоже на рекламу или спам (опросы, промо, #реклама) — из каналов такое не присылаю."
        )
        return

    data, _ = await llm.check_relevance(user.interest_query, text)
    if data is None:
        await message.answer("❌ LLM не смог разобрать объявление. Попробуй ещё раз.")
        return

    if not data.get("relevant"):
        await message.answer(
            "❌ По твоему запросу это не подходит.\n\n"
            f"Запрос: «{user.interest_query}»\n\n"
            "Попробуй уточнить /set_interest (например: «IT хакатоны», «MedTech хакатоны»)."
        )
        return

    deadline = data.get("deadline")
    if is_opportunity_expired(deadline, message.text):
        await message.answer(
            f"❌ Объявление устарело (дедлайн: {deadline or 'в прошлом'}).\n"
            "Из канала такое не пришлю."
        )
        return

    card_data = {
        "title": data.get("title") or "Возможность",
        "type": data.get("type") or "другое",
        "deadline": deadline or "не указан",
        "description": data.get("description") or message.text[:500],
        "requirements": data.get("requirements"),
        "source_channel_name": "тест (/test)",
        "message_link": "—",
        "application_url": data.get("application_url"),
    }
    await message.answer(
        "✅ Такое объявление пришло бы тебе из канала:\n\n" + format_match_card(card_data)
    )

"""Уведомления админу о новых категориях и вопросах по профилям."""

from __future__ import annotations

import json
import logging

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from bot.instance import get_notify_bot
from config import get_settings
from db.base import async_session_factory
from db.session import open_db_session
from db.repositories.interest_review import InterestReviewRepository
from db.repositories.users import SystemStateRepository, UserRepository
from services.interest_domains import (
    _APPROVED_DOMAINS_KEY,
    display_for_domain,
    parse_approved_domains,
)
from services.interest_profile import InterestProfile, parse_interest_profile

logger = logging.getLogger(__name__)


async def get_approved_domains() -> list[str]:
    async with async_session_factory() as session:
        raw = await SystemStateRepository(session).get(_APPROVED_DOMAINS_KEY)
    return parse_approved_domains(raw)


async def add_approved_domain(slug: str) -> list[str]:
    slug = slug.lower().strip().replace(" ", "_")
    if not slug:
        return await get_approved_domains()
    current = await get_approved_domains()
    if slug not in current:
        current.append(slug)
    async with async_session_factory() as session:
        await SystemStateRepository(session).set(_APPROVED_DOMAINS_KEY, json.dumps(current, ensure_ascii=False))
        await session.commit()
    return current


def _format_user_line(user_id: int, telegram_id: int, username: str | None) -> str:
    uname = f"@{username}" if username else "без username"
    return f"user db={user_id} tg={telegram_id} {uname}"


def _review_keyboard(request_id: int, domain: str) -> InlineKeyboardMarkup:
    safe = domain[:40]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ Добавить «{safe}»",
                    callback_data=f"interest_review:{request_id}:approve:{safe}",
                ),
                InlineKeyboardButton(
                    text="❌ Не нужно",
                    callback_data=f"interest_review:{request_id}:reject:{safe}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Все категории из запроса",
                    callback_data=f"interest_review:{request_id}:approve_all",
                ),
            ],
        ]
    )


async def submit_interest_for_admin_review(
    user_id: int,
    telegram_id: int,
    username: str | None,
    interest_query: str,
    profile: InterestProfile,
) -> int | None:
    if not profile.unknown_domains and not profile.admin_questions:
        return None

    async with async_session_factory() as session:
        repo = InterestReviewRepository(session)
        row = await repo.create(
            user_id,
            interest_query,
            proposed_domains=profile.unknown_domains,
            questions=profile.admin_questions,
        )
        await session.commit()
        request_id = row.id

    settings = get_settings()
    if not settings.telegram_admin_chat_id:
        return request_id

    lines = [
        "🆕 Профиль интересов — нужен твой ответ",
        "",
        _format_user_line(user_id, telegram_id, username),
        "",
        "📝 Запрос:",
        interest_query[:1200],
    ]

    if profile.types or profile.domains:
        auto = ", ".join([*profile.types, *profile.domains])
        lines.extend(["", f"🤖 Авто-категории: {auto}"])
    if profile.formats:
        fmt = ", ".join(profile.formats)
        lines.extend(["", f"📍 Формат: {fmt}"])

    if profile.unknown_domains:
        lines.extend(["", "🏷 Предложить новые категории:"])
        for domain in profile.unknown_domains:
            emoji, label = display_for_domain(domain)
            lines.append(f"  • {emoji} {label} (`{domain}`)")

    if profile.admin_questions:
        lines.extend(["", "❓ Вопросы по запросу:"])
        for q in profile.admin_questions:
            lines.append(f"  • {q}")

    text = "\n".join(lines)
    bot = get_notify_bot()
    keyboard = None
    if profile.unknown_domains:
        domain = profile.unknown_domains[0]
        keyboard = _review_keyboard(request_id, domain)
    elif profile.admin_questions:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Ок, всё понятно",
                        callback_data=f"interest_review:{request_id}:ok",
                    ),
                ]
            ]
        )
    try:
        await bot.send_message(settings.telegram_admin_chat_id, text, reply_markup=keyboard)
    except Exception as exc:
        logger.error("interest admin review notify failed: %s", exc)

    return request_id


async def save_user_interest_profile(
    user_id: int,
    interest_query: str,
    *,
    session: AsyncSession | None = None,
    telegram_id: int | None = None,
    username: str | None = None,
) -> InterestProfile:
    from services.interest_categorizer import categorize_interest

    profile, _source = await categorize_interest(
        interest_query,
        user_id=user_id,
    )

    async def _apply(sess: AsyncSession) -> None:
        user_repo = UserRepository(sess)
        user = await user_repo.get_by_id(user_id)
        if user:
            user.interest_query = interest_query.strip()
            user.interest_categories_json = json.dumps(profile.all_categories(), ensure_ascii=False)
            user.interest_preferences_json = profile.preferences_json()

    if session is not None:
        await _apply(session)
    else:
        async with open_db_session() as sess:
            await _apply(sess)
            await sess.commit()

    if telegram_id is not None:
        await submit_interest_for_admin_review(
            user_id,
            telegram_id,
            username,
            interest_query,
            profile,
        )

    return profile

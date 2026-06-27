from aiogram import F, Router
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

import json

from bot.filters import AdminFilter
from bot.callback_utils import safe_callback_answer
from config import get_settings
from db.repositories.interest_review import InterestReviewRepository
from db.repositories.users import UserRepository
from services.interest_admin_review import add_approved_domain, get_approved_domains
from services.interest_domains import display_for_domain
from services.interest_profile import parse_interest_profile

router = Router()


class AdminCallbackFilter(BaseFilter):
    async def __call__(self, callback: CallbackQuery) -> bool:
        if not callback.from_user:
            return False
        return get_settings().is_admin(callback.from_user.id)


@router.callback_query(F.data.startswith("interest_review:"), AdminCallbackFilter())
async def on_interest_review_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    request_id = int(parts[1])
    action = parts[2]
    domain = parts[3] if len(parts) > 3 else ""

    repo = InterestReviewRepository(session)
    row = await repo.get(request_id)
    if not row:
        await callback.answer("Запрос не найден", show_alert=True)
        return

    if action == "ok":
        await safe_callback_answer(callback, "Отмечено")
        await repo.resolve(request_id, status="acknowledged", admin_note="ok")
        await session.commit()
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    if action == "approve_all":
        proposed = json.loads(row.proposed_domains_json or "[]")
        await safe_callback_answer(callback, f"Добавлено категорий: {len(proposed)}")
        for item in proposed:
            await add_approved_domain(str(item))
        await repo.resolve(request_id, status="approved", admin_note="all")
        await session.commit()
        try:
            await callback.message.edit_text(
                (callback.message.text or "") + f"\n\n✅ Админ добавил: {', '.join(proposed)}"
            )
        except Exception:
            pass
        return

    if action == "approve" and domain:
        emoji, label = display_for_domain(domain)
        await safe_callback_answer(callback, f"Добавлено: {label}")
        await add_approved_domain(domain)
        user = await UserRepository(session).get_by_id(row.user_id)
        if user and user.interest_query:
            approved = await get_approved_domains()
            profile = parse_interest_profile(user.interest_query, approved_domains=approved)
            user.interest_categories_json = json.dumps(profile.all_categories(), ensure_ascii=False)
        await repo.resolve(request_id, status="approved", admin_note=domain)
        await session.commit()
        try:
            await callback.message.edit_text(
                (callback.message.text or "") + f"\n\n✅ Категория «{emoji} {label}» добавлена"
            )
        except Exception:
            pass
        return

    if action == "reject":
        await safe_callback_answer(callback, "Отклонено")
        await repo.resolve(request_id, status="rejected", admin_note=domain or None)
        await session.commit()
        try:
            await callback.message.edit_text((callback.message.text or "") + "\n\n❌ Категория отклонена")
        except Exception:
            pass
        return

    await callback.answer("Неизвестное действие", show_alert=True)


@router.message(AdminFilter(), F.text.startswith("/approve_domain"))
async def cmd_approve_domain(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /approve_domain femtech")
        return
    slug = parts[1].strip().lower()
    await add_approved_domain(slug)
    emoji, label = display_for_domain(slug)
    await message.answer(f"✅ Категория «{emoji} {label}» добавлена в одобренные.")

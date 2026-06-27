from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.event_types import AI_SEARCH
from config import get_settings
from db.repositories.users import EventRepository

# Казахстан (UTC+5), без zoneinfo/tzdata — работает на Windows
_KZ = timezone(timedelta(hours=5))


def ai_search_day_start_utc() -> datetime:
    local_now = datetime.now(_KZ)
    local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_start.astimezone(timezone.utc)

async def ai_search_usage(
    session: AsyncSession,
    user_id: int,
    *,
    telegram_id: int | None = None,
) -> dict[str, int]:
    settings = get_settings()
    limit = settings.ai_search_daily_limit
    if telegram_id is not None and settings.is_admin(telegram_id):
        return {"used": 0, "limit": limit, "remaining": 999999}
    used = await EventRepository(session).count_user_events_since(
        user_id, AI_SEARCH, ai_search_day_start_utc()
    )
    remaining = max(0, limit - used)
    return {"used": used, "limit": limit, "remaining": remaining}


async def enforce_ai_search_limit(
    session: AsyncSession,
    user_id: int,
    *,
    telegram_id: int | None = None,
) -> None:
    settings = get_settings()
    if telegram_id is not None and settings.is_admin(telegram_id):
        return
    stats = await ai_search_usage(session, user_id)
    if stats["remaining"] <= 0:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Лимит AI-поиска: {stats['limit']} раза в день. "
                "Попробуй завтра или смотри уже подобранные карточки в Каталоге."
            ),
        )

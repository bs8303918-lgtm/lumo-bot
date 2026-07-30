from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import DeadlineReminderLog


class DeadlineReminderLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def exists(self, user_id: int, catalog_id: int, window: str) -> bool:
        result = await self.session.execute(
            select(DeadlineReminderLog.id).where(
                DeadlineReminderLog.user_id == user_id,
                DeadlineReminderLog.catalog_id == catalog_id,
                DeadlineReminderLog.window == window,
            )
        )
        return result.scalar_one_or_none() is not None

    async def mark_sent(self, user_id: int, catalog_id: int, window: str) -> None:
        self.session.add(
            DeadlineReminderLog(user_id=user_id, catalog_id=catalog_id, window=window)
        )

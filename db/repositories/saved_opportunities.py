"""Избранные конкурсы с трекингом статуса подачи (interested/applied/interview/result)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import CatalogOpportunity, SavedOpportunity, User

SAVED_STATUSES = ("interested", "applied", "interview", "result")


class SavedOpportunityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_user(self, user_id: int) -> list[SavedOpportunity]:
        result = await self.session.execute(
            select(SavedOpportunity)
            .where(SavedOpportunity.user_id == user_id)
            .options(selectinload(SavedOpportunity.catalog))
            .order_by(SavedOpportunity.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, user_id: int, catalog_id: int) -> SavedOpportunity | None:
        result = await self.session.execute(
            select(SavedOpportunity).where(
                SavedOpportunity.user_id == user_id,
                SavedOpportunity.catalog_id == catalog_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: int,
        catalog_id: int,
        *,
        status: str | None = None,
    ) -> SavedOpportunity:
        existing = await self.get(user_id, catalog_id)
        if existing:
            if status:
                existing.status = status
            return existing
        row = SavedOpportunity(
            user_id=user_id,
            catalog_id=catalog_id,
            status=status or "interested",
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def remove(self, user_id: int, catalog_id: int) -> bool:
        row = await self.get(user_id, catalog_id)
        if not row:
            return False
        await self.session.delete(row)
        return True

    async def count_opted_in_peers(
        self,
        catalog_id: int,
        *,
        exclude_user_id: int,
        region: str | None = None,
    ) -> tuple[int, int]:
        """(total opt-in peers, opt-in peers in the same region) — no identities exposed.

        Region matching is done in Python (not SQL lower()) — SQLite's lower() is
        ASCII-only and silently fails to case-fold Cyrillic region names.
        """
        stmt = (
            select(SavedOpportunity.user_id, User.region)
            .join(User, User.id == SavedOpportunity.user_id)
            .distinct()
            .where(
                SavedOpportunity.catalog_id == catalog_id,
                SavedOpportunity.user_id != exclude_user_id,
                User.visible_in_community.is_(True),
            )
        )
        rows = (await self.session.execute(stmt)).all()
        total = len(rows)
        same_region = 0
        needle = (region or "").strip().lower()
        if needle:
            same_region = sum(1 for _user_id, row_region in rows if (row_region or "").strip().lower() == needle)
        return total, same_region

    async def list_active_for_reminders(self) -> list[SavedOpportunity]:
        """Всё, что ещё не 'result' и не отписано от уведомлений — кандидаты на напоминания."""
        result = await self.session.execute(
            select(SavedOpportunity)
            .where(SavedOpportunity.status != "result", SavedOpportunity.notify_opt_in.is_(True))
            .options(
                selectinload(SavedOpportunity.catalog).selectinload(CatalogOpportunity.raw_message),
                selectinload(SavedOpportunity.user),
            )
        )
        return list(result.scalars().all())

"""Mentor workspace: kanban applications and shortlists."""

from __future__ import annotations

import secrets
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import MentorApplication, MentorShortlist, MentorShortlistItem

KANBAN_STATUSES = ("todo", "in_progress", "submitted")


def _slug() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(10))


class MentorWorkspaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_applications(self, user_id: int) -> list[MentorApplication]:
        result = await self.session.execute(
            select(MentorApplication)
            .where(MentorApplication.user_id == user_id)
            .order_by(MentorApplication.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_application(self, user_id: int, app_id: int) -> MentorApplication | None:
        result = await self.session.execute(
            select(MentorApplication).where(
                MentorApplication.user_id == user_id,
                MentorApplication.id == app_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_application(
        self,
        user_id: int,
        *,
        catalog_id: int,
        student_name: str = "Студент",
        status: str = "todo",
        notes: str | None = None,
    ) -> MentorApplication:
        result = await self.session.execute(
            select(MentorApplication).where(
                MentorApplication.user_id == user_id,
                MentorApplication.catalog_id == catalog_id,
                MentorApplication.student_name == student_name,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.status = status
            if notes is not None:
                existing.notes = notes
            await self.session.flush()
            return existing

        app = MentorApplication(
            user_id=user_id,
            catalog_id=catalog_id,
            student_name=student_name[:120],
            status=status if status in KANBAN_STATUSES else "todo",
            notes=notes,
        )
        self.session.add(app)
        await self.session.flush()
        return app

    async def update_application(
        self,
        app: MentorApplication,
        *,
        status: str | None = None,
        student_name: str | None = None,
        notes: str | None = None,
    ) -> MentorApplication:
        if status and status in KANBAN_STATUSES:
            app.status = status
        if student_name is not None:
            app.student_name = student_name[:120]
        if notes is not None:
            app.notes = notes
        await self.session.flush()
        return app

    async def delete_application(self, app: MentorApplication) -> None:
        await self.session.delete(app)

    async def list_shortlists(self, user_id: int) -> list[MentorShortlist]:
        result = await self.session.execute(
            select(MentorShortlist)
            .where(MentorShortlist.user_id == user_id)
            .order_by(MentorShortlist.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_shortlist(
        self,
        user_id: int,
        *,
        title: str,
        agency_name: str,
        catalog_ids: list[int],
    ) -> MentorShortlist:
        shortlist = MentorShortlist(
            user_id=user_id,
            title=title[:200],
            agency_name=agency_name[:120],
            slug=_slug(),
        )
        self.session.add(shortlist)
        await self.session.flush()
        for idx, catalog_id in enumerate(catalog_ids):
            self.session.add(
                MentorShortlistItem(
                    shortlist_id=shortlist.id,
                    catalog_id=catalog_id,
                    sort_order=idx,
                )
            )
        await self.session.flush()
        return shortlist

    async def get_shortlist_by_slug(self, slug: str) -> MentorShortlist | None:
        result = await self.session.execute(
            select(MentorShortlist)
            .where(MentorShortlist.slug == slug)
            .options(selectinload(MentorShortlist.items))
        )
        return result.scalar_one_or_none()

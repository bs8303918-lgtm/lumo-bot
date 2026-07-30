from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import MentorRequest


class MentorRequestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_existing(self, student_user_id: int, catalog_id: int) -> MentorRequest | None:
        result = await self.session.execute(
            select(MentorRequest).where(
                MentorRequest.student_user_id == student_user_id,
                MentorRequest.catalog_id == catalog_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        student_user_id: int,
        catalog_id: int,
        message: str | None,
    ) -> MentorRequest:
        row = MentorRequest(student_user_id=student_user_id, catalog_id=catalog_id, message=message)
        self.session.add(row)
        await self.session.flush()
        return row

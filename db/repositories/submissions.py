from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from db.models import OpportunitySubmission, User


class SubmissionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        source_mode: str,
        title: str | None = None,
        opportunity_type: str | None = None,
        description: str | None = None,
        deadline: str | None = None,
        location: str | None = None,
        link: str | None = None,
    ) -> OpportunitySubmission:
        row = OpportunitySubmission(
            user_id=user_id,
            source_mode=source_mode,
            title=title,
            opportunity_type=opportunity_type,
            description=description,
            deadline=deadline,
            location=location,
            link=link,
            status="pending",
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_by_id(self, submission_id: int) -> OpportunitySubmission | None:
        result = await self.session.execute(
            select(OpportunitySubmission)
            .options(joinedload(OpportunitySubmission.user))
            .where(OpportunitySubmission.id == submission_id)
        )
        return result.scalar_one_or_none()

    async def list_by_status(self, status: str, *, limit: int = 30) -> list[OpportunitySubmission]:
        result = await self.session.execute(
            select(OpportunitySubmission)
            .options(joinedload(OpportunitySubmission.user))
            .where(OpportunitySubmission.status == status)
            .order_by(OpportunitySubmission.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def list_for_user(self, user_id: int, *, limit: int = 20) -> list[OpportunitySubmission]:
        result = await self.session.execute(
            select(OpportunitySubmission)
            .where(OpportunitySubmission.user_id == user_id)
            .order_by(OpportunitySubmission.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_pending(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(OpportunitySubmission)
            .where(OpportunitySubmission.status == "pending")
        )
        return int(result.scalar_one())

    async def mark_reviewed(
        self,
        submission: OpportunitySubmission,
        *,
        status: str,
        catalog_id: int | None = None,
        admin_note: str | None = None,
    ) -> OpportunitySubmission:
        submission.status = status
        submission.catalog_id = catalog_id
        submission.admin_note = admin_note
        submission.reviewed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return submission

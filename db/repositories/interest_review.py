import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import InterestReviewRequest


class InterestReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        interest_query: str,
        *,
        proposed_domains: list[str],
        questions: list[str],
    ) -> InterestReviewRequest:
        row = InterestReviewRequest(
            user_id=user_id,
            interest_query=interest_query,
            proposed_domains_json=json.dumps(proposed_domains, ensure_ascii=False) if proposed_domains else None,
            questions_json=json.dumps(questions, ensure_ascii=False) if questions else None,
            status="pending",
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get(self, request_id: int) -> InterestReviewRequest | None:
        result = await self.session.execute(
            select(InterestReviewRequest).where(InterestReviewRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def resolve(self, request_id: int, *, status: str, admin_note: str | None = None) -> None:
        row = await self.get(request_id)
        if not row:
            return
        row.status = status
        row.admin_note = admin_note
        row.resolved_at = datetime.now(timezone.utc)

    async def list_pending(self, limit: int = 20) -> list[InterestReviewRequest]:
        result = await self.session.execute(
            select(InterestReviewRequest)
            .where(InterestReviewRequest.status == "pending")
            .order_by(InterestReviewRequest.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import CatalogOpportunity, OpportunityReview


class OpportunityReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_catalog(self, catalog_id: int, *, limit: int = 30) -> list[OpportunityReview]:
        result = await self.session.execute(
            select(OpportunityReview)
            .where(OpportunityReview.catalog_id == catalog_id)
            .order_by(OpportunityReview.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent(self, *, limit: int = 30) -> list[OpportunityReview]:
        result = await self.session.execute(
            select(OpportunityReview)
            .options(selectinload(OpportunityReview.catalog))
            .order_by(OpportunityReview.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(
        self,
        *,
        catalog_id: int,
        user_id: int,
        title: str,
        body: str,
        link: str | None,
        author_display_name: str,
    ) -> OpportunityReview:
        row = OpportunityReview(
            catalog_id=catalog_id,
            user_id=user_id,
            title=title,
            body=body,
            link=link or None,
            author_display_name=author_display_name,
        )
        self.session.add(row)
        await self.session.flush()
        return row


def serialize_review(review: OpportunityReview, *, include_catalog: bool = False) -> dict:
    payload = {
        "id": review.id,
        "catalogId": review.catalog_id,
        "title": review.title,
        "body": review.body,
        "link": review.link,
        "author": review.author_display_name,
        "createdAt": review.created_at.isoformat() if review.created_at else None,
    }
    if include_catalog:
        catalog: CatalogOpportunity | None = getattr(review, "catalog", None)
        payload["contest"] = catalog.title if catalog else None
    return payload

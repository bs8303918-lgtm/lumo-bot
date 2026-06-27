import json
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ContactLead, Course, ExpertService, Grant, SentMatch


def _parse_features(raw: str) -> list[str]:
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_templates(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


class GrantRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_dict(self, grant: Grant, *, include_premium: bool) -> dict:
        item = {
            "id": grant.id,
            "flag": grant.flag,
            "location": grant.location,
            "title": grant.title,
            "description": grant.description,
            "deadline": grant.deadline,
            "features": _parse_features(grant.features_json),
            "isPremium": grant.is_premium,
        }
        if include_premium:
            item["premiumContent"] = {
                "applicationUrl": grant.application_url,
                "messageLink": grant.message_link,
                "requirements": grant.requirements,
                "documentTemplates": _parse_templates(grant.document_templates_json),
                "sourceChannelName": grant.source_channel_name,
            }
            item["isLocked"] = False
        elif grant.is_premium:
            item["isLocked"] = True
            item["premiumContent"] = None
        else:
            item["isLocked"] = False
            item["premiumContent"] = {
                "applicationUrl": grant.application_url,
                "messageLink": grant.message_link,
                "requirements": grant.requirements,
                "documentTemplates": _parse_templates(grant.document_templates_json),
                "sourceChannelName": grant.source_channel_name,
            }
        return item

    async def list_published(self, query: str | None = None) -> list[dict]:
        stmt = select(Grant).where(Grant.is_published.is_(True)).order_by(Grant.created_at.desc())
        if query:
            pattern = f"%{query.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Grant.title).like(pattern),
                    func.lower(Grant.location).like(pattern),
                    func.lower(Grant.description).like(pattern),
                )
            )
        result = await self.session.execute(stmt)
        grants = list(result.scalars().all())
        return [self._to_dict(g, include_premium=False) for g in grants]

    async def get_published(self, grant_id: int, *, include_premium: bool) -> dict | None:
        result = await self.session.execute(
            select(Grant).where(Grant.id == grant_id, Grant.is_published.is_(True))
        )
        grant = result.scalar_one_or_none()
        if not grant:
            return None
        return self._to_dict(grant, include_premium=include_premium)

    async def count_published(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Grant).where(Grant.is_published.is_(True))
        )
        return result.scalar_one()

    async def import_from_sent_matches(self) -> int:
        subq = (
            select(
                SentMatch.title,
                func.max(SentMatch.id).label("max_id"),
            )
            .group_by(SentMatch.title)
            .subquery()
        )
        result = await self.session.execute(
            select(SentMatch).join(subq, SentMatch.id == subq.c.max_id).order_by(SentMatch.sent_at.desc())
        )
        matches = list(result.scalars().all())
        imported = 0
        for match in matches:
            existing = await self.session.execute(select(Grant.id).where(Grant.title == match.title).limit(1))
            if existing.scalar_one_or_none():
                continue
            features = []
            if match.requirements:
                features.append(match.requirements[:120])
            if match.opportunity_type:
                features.append(match.opportunity_type.capitalize())
            grant = Grant(
                flag="🇰🇿",
                location=f"Telegram | {match.source_channel_name}",
                title=match.title,
                description=match.description,
                deadline=match.deadline,
                features_json=json.dumps(features, ensure_ascii=False),
                is_premium=bool(match.application_url),
                application_url=match.application_url,
                message_link=match.message_link,
                requirements=match.requirements,
                source_channel_name=match.source_channel_name,
            )
            self.session.add(grant)
            imported += 1
        if imported:
            await self.session.flush()
        return imported


class CatalogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_services(self) -> list[dict]:
        result = await self.session.execute(
            select(ExpertService)
            .where(ExpertService.is_active.is_(True))
            .order_by(ExpertService.sort_order, ExpertService.id)
        )
        return [
            {"id": s.id, "title": s.title, "price": s.price_display}
            for s in result.scalars().all()
        ]

    async def list_courses(self) -> list[dict]:
        result = await self.session.execute(
            select(Course).where(Course.is_active.is_(True)).order_by(Course.id)
        )
        return [
            {
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "price": c.price_display,
            }
            for c in result.scalars().all()
        ]

    async def get_primary_course(self) -> dict | None:
        courses = await self.list_courses()
        return courses[0] if courses else None


class LeadRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        contact: str,
        name: str | None = None,
        message: str | None = None,
        grant_id: int | None = None,
        lead_type: str = "contact",
    ) -> ContactLead:
        lead = ContactLead(
            name=name,
            contact=contact,
            message=message,
            grant_id=grant_id,
            lead_type=lead_type,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(lead)
        await self.session.flush()
        return lead

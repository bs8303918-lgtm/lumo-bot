"""Team Finder profiles repository."""

from __future__ import annotations

import json

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import TeamProfile, User


class TeamProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: int) -> TeamProfile | None:
        result = await self.session.execute(
            select(TeamProfile).where(TeamProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_id(self, profile_id: int) -> TeamProfile | None:
        result = await self.session.execute(
            select(TeamProfile).where(TeamProfile.id == profile_id, TeamProfile.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def list_active(
        self,
        *,
        mode: str | None = None,
        role: str | None = None,
        city: str | None = None,
        exclude_user_id: int | None = None,
        limit: int = 50,
    ) -> list[TeamProfile]:
        stmt: Select = (
            select(TeamProfile)
            .where(TeamProfile.is_active.is_(True))
            .order_by(TeamProfile.updated_at.desc())
            .limit(limit)
        )
        if mode:
            stmt = stmt.where(TeamProfile.mode == mode)
        if role:
            stmt = stmt.where(TeamProfile.role == role)
        if city:
            stmt = stmt.where(TeamProfile.city == city)
        if exclude_user_id:
            stmt = stmt.where(TeamProfile.user_id != exclude_user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(
        self,
        user: User,
        *,
        mode: str,
        display_name: str,
        role: str,
        city: str,
        raw_prompt: str,
        skills: list[str],
        telegram_contact: str | None,
    ) -> TeamProfile:
        existing = await self.get_by_user_id(user.id)
        skills_json = json.dumps(skills, ensure_ascii=False)
        if existing:
            existing.mode = mode
            existing.display_name = display_name
            existing.role = role
            existing.city = city
            existing.raw_prompt = raw_prompt
            existing.skills_json = skills_json
            existing.telegram_contact = telegram_contact
            existing.is_active = True
            await self.session.flush()
            return existing

        profile = TeamProfile(
            user_id=user.id,
            mode=mode,
            display_name=display_name,
            role=role,
            city=city,
            raw_prompt=raw_prompt,
            skills_json=skills_json,
            telegram_contact=telegram_contact,
            is_active=True,
        )
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def deactivate(self, user_id: int) -> bool:
        profile = await self.get_by_user_id(user_id)
        if not profile:
            return False
        profile.is_active = False
        await self.session.flush()
        return True

"""Team Finder API — анкеты с ИИ-категоризацией."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.deps import get_db
from db.models import TeamProfile, User
from db.repositories.team_profiles import TeamProfileRepository
from services.team_catalog import (
    TEAM_CITIES,
    TEAM_MODES,
    TEAM_ROLES,
    city_label,
    role_label,
    skill_label,
    team_meta_payload,
)
from services.team_profile import (
    categorize_team_profile,
    score_profile_match,
    skills_from_json,
)

router = APIRouter(tags=["team"])


class TeamProfileRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=300)
    mode: str | None = Field(default=None)
    displayName: str | None = Field(default=None, max_length=20)
    telegram: str | None = Field(default=None, max_length=64)


def _telegram_url(contact: str | None, user: User | None) -> str | None:
    raw = (contact or "").strip()
    if not raw and user:
        raw = (user.username or "").strip()
    if not raw:
        return None
    handle = raw.lstrip("@")
    if handle.startswith("http"):
        return handle
    return f"https://t.me/{handle}"


def _serialize_profile(
    profile: TeamProfile,
    user: User | None = None,
    *,
    viewer_user_id: int | None = None,
) -> dict:
    skills = skills_from_json(profile.skills_json)
    linked_user = user
    return {
        "id": profile.id,
        "displayName": profile.display_name,
        "mode": profile.mode,
        "modeLabel": "Ищу команду" if profile.mode == "seeking_team" else "Ищем человека",
        "role": profile.role,
        "roleLabel": role_label(profile.role),
        "city": profile.city,
        "cityLabel": city_label(profile.city),
        "skills": skills,
        "skillLabels": [skill_label(s) for s in skills],
        "description": profile.raw_prompt,
        "telegramContact": profile.telegram_contact or (linked_user.username if linked_user else None),
        "telegramUrl": _telegram_url(profile.telegram_contact, linked_user),
        "isOwn": viewer_user_id is not None and profile.user_id == viewer_user_id,
        "updatedAt": profile.updated_at.isoformat() if profile.updated_at else None,
    }


@router.get("/team/meta")
async def team_meta() -> dict:
    return team_meta_payload()


@router.get("/team/profiles")
async def list_team_profiles(
    mode: str | None = Query(default=None),
    role: str | None = Query(default=None),
    city: str | None = Query(default=None),
    query: str | None = Query(default=None, max_length=300),
    limit: int = Query(default=30, ge=1, le=60),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    repo = TeamProfileRepository(session)
    if mode and mode not in TEAM_MODES:
        raise HTTPException(status_code=400, detail="Invalid mode")
    if role and role not in TEAM_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    if city and city not in TEAM_CITIES:
        raise HTTPException(status_code=400, detail="Invalid city")

    wanted_skills: list[str] = []
    filter_role = role
    filter_mode = mode
    search_message: str | None = None

    if query and query.strip():
        parsed = await categorize_team_profile(query.strip())
        wanted_skills = parsed.skills
        if not filter_role and parsed.role != "other":
            filter_role = parsed.role
        if not filter_mode:
            filter_mode = parsed.mode
        search_message = (
            f"ИИ подобрал: {role_label(parsed.role)}, "
            f"{', '.join(skill_label(s) for s in parsed.skills[:4]) or 'без тегов'}"
        )

    profiles = await repo.list_active(
        mode=filter_mode,
        role=filter_role if not (query and wanted_skills) else filter_role,
        city=city,
        exclude_user_id=user.id,
        limit=limit * 3 if query else limit,
    )

    if query and query.strip():
        scored = [
            (
                score_profile_match(
                    skills_from_json(p.skills_json),
                    p.role,
                    wanted_skills=wanted_skills,
                    wanted_role=filter_role,
                ),
                p,
            )
            for p in profiles
        ]
        scored.sort(key=lambda item: (item[0], item[1].updated_at.timestamp() if item[1].updated_at else 0), reverse=True)
        profiles = [p for score, p in scored if score > 0][:limit]
        if not profiles:
            profiles = [p for _, p in scored][:limit]
    else:
        profiles = profiles[:limit]

    user_ids = {p.user_id for p in profiles}
    users_map: dict[int, User] = {}
    if user_ids:
        from sqlalchemy import select as sa_select

        result = await session.execute(sa_select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u for u in result.scalars().all()}

    return {
        "items": [
            _serialize_profile(p, users_map.get(p.user_id), viewer_user_id=user.id) for p in profiles
        ],
        "total": len(profiles),
        "searchMessage": search_message,
        "parsed": {
            "role": filter_role,
            "skills": wanted_skills,
        }
        if query
        else None,
    }


@router.get("/team/profile/me")
async def get_my_team_profile(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    profile = await TeamProfileRepository(session).get_by_user_id(user.id)
    if not profile or not profile.is_active:
        return {"profile": None}
    return {"profile": _serialize_profile(profile, user, viewer_user_id=user.id)}


@router.post("/team/profile")
async def save_team_profile(
    body: TeamProfileRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    prompt = body.prompt.strip()
    parsed = await categorize_team_profile(
        prompt,
        mode_hint=body.mode,
        display_name_hint=body.displayName or user.display_name or user.username,
    )

    display_name = (body.displayName or parsed.display_name or user.display_name or user.username or "Участник").strip()
    display_name = display_name[:20] or "Участник"

    telegram = (body.telegram or user.username or "").strip() or None
    if telegram and not telegram.startswith("@") and "t.me" not in telegram:
        telegram = f"@{telegram.lstrip('@')}"

    profile = await TeamProfileRepository(session).upsert(
        user,
        mode=parsed.mode,
        display_name=display_name,
        role=parsed.role,
        city=parsed.city,
        raw_prompt=prompt,
        skills=parsed.skills,
        telegram_contact=telegram,
    )
    await session.commit()

    return {
        "profile": _serialize_profile(profile, user, viewer_user_id=user.id),
        "parsed": {
            "mode": parsed.mode,
            "role": parsed.role,
            "city": parsed.city,
            "skills": parsed.skills,
            "source": parsed.source,
        },
        "message": "Анкета сохранена — ИИ разметил навыки и роль",
    }


@router.delete("/team/profile/me")
async def delete_my_team_profile(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    ok = await TeamProfileRepository(session).deactivate(user.id)
    await session.commit()
    if not ok:
        raise HTTPException(status_code=404, detail="Анкета не найдена")
    return {"ok": True}

"""Категоризация анкет Team Finder: локально + LLM."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from config import get_settings
from llm.client import LLMClient
from services.team_catalog import (
    TEAM_MODES,
    TEAM_ROLES,
    TEAM_CITIES,
    extract_city_local,
    extract_mode_local,
    extract_role_local,
    extract_skills_local,
    normalize_skill_slug,
    skills_catalog_for_prompt,
)

logger = logging.getLogger(__name__)


@dataclass
class TeamProfileParsed:
    mode: str = "seeking_team"
    role: str = "other"
    city: str = "online"
    skills: list[str] = field(default_factory=list)
    display_name: str | None = None
    source: str = "local"


def _merge_skills(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        for item in group:
            slug = normalize_skill_slug(item) or item
            if slug and slug not in merged:
                merged.append(slug)
    return merged[:12]


def _normalize_mode(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    return value if value in TEAM_MODES else extract_mode_local(value)


def _normalize_role(raw: str | None, text: str) -> str:
    value = (raw or "").strip().lower().replace(" ", "_")
    if value in TEAM_ROLES:
        return value
    return extract_role_local(text) or "other"


def _normalize_city(raw: str | None, text: str) -> str:
    value = (raw or "").strip().lower().replace(" ", "_")
    if value in TEAM_CITIES:
        return value
    return extract_city_local(text) or "online"


def parse_team_profile_local(text: str, *, mode_hint: str | None = None) -> TeamProfileParsed:
    body = (text or "").strip()
    mode = _normalize_mode(mode_hint) if mode_hint else extract_mode_local(body)
    return TeamProfileParsed(
        mode=mode,
        role=_normalize_role(None, body),
        city=_normalize_city(None, body),
        skills=extract_skills_local(body),
        source="local",
    )


def _needs_llm(parsed: TeamProfileParsed) -> bool:
    if parsed.role == "other" and not parsed.skills:
        return True
    if len(parsed.skills) < 1:
        return True
    return False


async def categorize_team_profile(
    text: str,
    *,
    mode_hint: str | None = None,
    display_name_hint: str | None = None,
    skip_llm: bool = False,
) -> TeamProfileParsed:
    body = (text or "").strip()
    parsed = parse_team_profile_local(body, mode_hint=mode_hint)
    if display_name_hint:
        parsed.display_name = display_name_hint.strip()[:20] or None

    settings = get_settings()
    if (
        not skip_llm
        and settings.llm_interest_categorization
        and settings.llm_user_configured
        and _needs_llm(parsed)
    ):
        try:
            data, _raw = await LLMClient().extract_team_profile(body)
            if data:
                llm_skills = data.get("skills") or []
                if isinstance(llm_skills, list):
                    parsed.skills = _merge_skills(parsed.skills, [str(s) for s in llm_skills])
                parsed.role = _normalize_role(data.get("role"), body)
                parsed.city = _normalize_city(data.get("city"), body)
                parsed.mode = _normalize_mode(data.get("mode") or parsed.mode)
                if not parsed.display_name and data.get("display_name"):
                    name = str(data["display_name"]).strip()
                    parsed.display_name = name[:20] if name else None
                parsed.source = "hybrid" if parsed.source == "local" else "llm"
        except Exception as exc:
            logger.warning("Team profile LLM categorization failed: %s", exc)

    if not parsed.skills and parsed.role in TEAM_ROLES and parsed.role != "other":
        parsed.skills = [parsed.role] if parsed.role in {"frontend", "backend", "mobile", "design", "devops"} else []

    return parsed


def skills_from_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x) for x in data if x]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def score_profile_match(
    profile_skills: list[str],
    profile_role: str,
    *,
    wanted_skills: list[str],
    wanted_role: str | None,
) -> int:
    score = 0
    skill_set = set(profile_skills)
    for skill in wanted_skills:
        if skill in skill_set:
            score += 3
    if wanted_role and wanted_role != "other" and profile_role == wanted_role:
        score += 4
    elif wanted_role and wanted_role != "other":
        # partial: backend vs python overlap already counted
        pass
    return score

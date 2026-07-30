"""Структурированный профиль ученика: класс, регион, английский, предметы/интересы."""

from __future__ import annotations

import json

from db.models import User

ENGLISH_LEVELS: tuple[str, ...] = ("none", "a1", "a2", "b1", "b2", "c1", "c2", "native")

_ENGLISH_REQUIREMENT_MARKERS: dict[str, tuple[str, ...]] = {
    "b2": ("ielts 5.5", "ielts 6", "toefl 70", "upper-intermediate", "b2"),
    "c1": ("ielts 6.5", "ielts 7", "toefl 90", "advanced", "c1"),
    "c2": ("ielts 8", "toefl 110", "native speaker", "c2"),
}

_ENGLISH_RANK = {level: idx for idx, level in enumerate(ENGLISH_LEVELS)}


def normalize_english_level(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip().lower()
    return value if value in ENGLISH_LEVELS else None


def parse_subjects(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()][:12]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def subjects_to_json(subjects: list[str]) -> str:
    cleaned = [s.strip() for s in subjects if s and s.strip()][:12]
    return json.dumps(cleaned, ensure_ascii=False)


def serialize_student_profile(user: User) -> dict:
    return {
        "grade": user.grade,
        "region": user.region,
        "englishLevel": user.english_level,
        "subjects": parse_subjects(user.subjects_json),
        "visibleInCommunity": bool(user.visible_in_community),
    }


def entry_required_english_level(blob: str) -> str | None:
    """Грубая эвристика: какой уровень английского упомянут в требованиях/описании."""
    lowered = (blob or "").lower()
    if not lowered:
        return None
    best: str | None = None
    for level, markers in _ENGLISH_REQUIREMENT_MARKERS.items():
        if any(marker in lowered for marker in markers):
            if best is None or _ENGLISH_RANK[level] > _ENGLISH_RANK[best]:
                best = level
    return best


def english_level_gap(user_level: str | None, required_level: str | None) -> float:
    """Штраф релевантности, если английского пользователя не хватает под требование поста."""
    if not required_level:
        return 0.0
    if not user_level or user_level not in _ENGLISH_RANK:
        return 0.0
    if _ENGLISH_RANK[user_level] >= _ENGLISH_RANK[required_level]:
        return 0.0
    return float(_ENGLISH_RANK[required_level] - _ENGLISH_RANK[user_level])

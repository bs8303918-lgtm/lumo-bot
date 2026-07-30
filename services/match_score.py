"""Match score % — насколько конкурс совпадает с профилем пользователя (0-100)."""

from __future__ import annotations

import math

from db.models import CatalogOpportunity, User
from services.interest_matcher import entry_all_tags, relevance_score
from services.interest_profile import parse_format_preferences
from services.student_profile import english_level_gap, entry_required_english_level

_SATURATION_K = 6.0


def _entry_blob(entry: CatalogOpportunity) -> str:
    return " ".join(
        filter(
            None,
            [entry.title, entry.description, entry.requirements or "", " ".join(entry_all_tags(entry))],
        )
    )


def _region_bonus(user: User, entry: CatalogOpportunity) -> float:
    region = (user.region or "").strip().lower()
    if not region or len(region) < 3:
        return 0.0
    blob = _entry_blob(entry).lower()
    return 1.5 if region in blob else 0.0


def raw_match_score(user: User, entry: CatalogOpportunity) -> float:
    """Необрезанный скор — сигналы профиля поверх relevance_score."""
    interest_query = (user.interest_query or "").strip()
    format_preferences = parse_format_preferences(user.interest_preferences_json)

    if not interest_query:
        # Без явного интереса ориентируемся только на профильные сигналы.
        score = 2.0
    else:
        score = relevance_score(interest_query, entry, format_preferences=format_preferences)
        if score <= 0.0:
            return 0.0

    score += _region_bonus(user, entry)

    required_level = entry_required_english_level(_entry_blob(entry))
    penalty = english_level_gap(user.english_level, required_level)
    if penalty:
        score = max(0.0, score - penalty * 1.5)

    return score


def score_to_percent(score: float) -> int:
    """Насыщающаяся кривая: 0 -> 0%, ~3 (порог совпадения) -> ~39%, ~10 -> ~81%."""
    if score <= 0:
        return 0
    percent = 100.0 * (1.0 - math.exp(-score / _SATURATION_K))
    return max(1, min(100, round(percent)))


def compute_match_score(user: User, entry: CatalogOpportunity) -> int:
    """Публичный match score % для карточки/детали конкурса."""
    return score_to_percent(raw_match_score(user, entry))

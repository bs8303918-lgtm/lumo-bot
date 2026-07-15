"""ИИ-оценка шансов студента на конкретную программу."""

from __future__ import annotations

import logging

from config import get_settings
from db.models import CatalogOpportunity
from llm.client import LLMClient
from services.webapp_catalog import format_entry_deadline_label

logger = logging.getLogger(__name__)


def _fallback_evaluation(student_profile: str, entry: CatalogOpportunity) -> dict:
    profile = (student_profile or "").strip().lower()
    req = (entry.requirements or entry.description or "").strip().lower()
    overlap = sum(1 for token in profile.split() if len(token) > 4 and token in req)
    score = min(85, 35 + overlap * 8)
    return {
        "score": score,
        "verdict": "Предварительная оценка без ИИ — уточните профиль студента для точного расчёта.",
        "strengths": ["Профиль заполнен — можно сопоставить с требованиями программы"],
        "gaps": ["Добавьте оценки, проекты и достижения для точной оценки"],
        "source": "fallback",
    }


async def evaluate_profile_fit(student_profile: str, entry: CatalogOpportunity) -> dict:
    body = (student_profile or "").strip()
    if len(body) < 10:
        return {
            "score": 0,
            "verdict": "Опишите профиль студента подробнее (минимум 10 символов).",
            "strengths": [],
            "gaps": ["Нет данных о достижениях, оценках и целях"],
            "source": "validation",
        }

    deadline_meta = format_entry_deadline_label(entry, is_archived=not entry.is_active)
    settings = get_settings()
    if settings.llm_user_configured:
        try:
            data, _raw = await LLMClient().evaluate_profile_fit(
                student_profile=body,
                title=entry.title,
                opp_type=entry.opportunity_type,
                description=entry.description,
                requirements=entry.requirements,
                deadline=deadline_meta.get("label"),
            )
            if data and isinstance(data.get("score"), (int, float)):
                score = max(0, min(100, int(data["score"])))
                strengths = data.get("strengths") or []
                gaps = data.get("gaps") or []
                return {
                    "score": score,
                    "verdict": str(data.get("verdict") or "").strip() or "Оценка готова.",
                    "strengths": [str(s) for s in strengths if s][:6],
                    "gaps": [str(g) for g in gaps if g][:6],
                    "source": "llm",
                }
        except Exception as exc:
            logger.warning("Profile evaluator LLM failed: %s", exc)

    return _fallback_evaluation(body, entry)

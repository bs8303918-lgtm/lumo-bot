"""AI-саммари в 3-4 буллетах + чеклист требований — кэшируется на карточке конкурса."""

from __future__ import annotations

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.models import CatalogOpportunity
from services.interest_matcher import CATEGORY_DISPLAY

logger = logging.getLogger(__name__)

DEFAULT_CHECKLIST = [
    "Прочитать условия участия по ссылке",
    "Подготовить нужные документы до дедлайна",
    "Подать заявку через форму организатора",
]

_REQUIREMENT_MARKERS: tuple[tuple[str, str], ...] = (
    ("эссе", "Эссе / мотивационное письмо"),
    ("essay", "Эссе / мотивационное письмо"),
    ("рекоменд", "Рекомендательное письмо"),
    ("recommendation", "Рекомендательное письмо"),
    ("портфолио", "Портфолио"),
    ("portfolio", "Портфолио"),
    ("резюме", "Резюме / CV"),
    ("cv", "Резюме / CV"),
    ("транскрипт", "Транскрипт / табель оценок"),
    ("табел", "Транскрипт / табель оценок"),
    ("ielts", "Сертификат английского (IELTS/TOEFL)"),
    ("toefl", "Сертификат английского (IELTS/TOEFL)"),
    ("видео", "Видеопрезентация"),
    ("video", "Видеопрезентация"),
    ("команд", "Команда участников"),
)


def _parse_list(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, list) and data:
            return [str(x) for x in data]
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def _heuristic_summary(entry: CatalogOpportunity) -> list[str]:
    _, label = CATEGORY_DISPLAY.get(entry.opportunity_type, ("📌", entry.opportunity_type.capitalize()))
    description = (entry.description or "").strip()
    snippet = description[:180] + ("…" if len(description) > 180 else "")
    bullets = [f"Тип: {label}"]
    if snippet:
        bullets.append(snippet)
    bullets.append(f"Дедлайн: {entry.deadline or 'не указан'}")
    if entry.requirements:
        bullets.append(f"Требуется: {entry.requirements[:160]}")
    return bullets[:4]


def _heuristic_checklist(entry: CatalogOpportunity) -> list[str]:
    blob = " ".join(filter(None, [entry.requirements, entry.description])).lower()
    found = [label for marker, label in _REQUIREMENT_MARKERS if marker in blob]
    seen: list[str] = []
    for item in found:
        if item not in seen:
            seen.append(item)
    return seen or list(DEFAULT_CHECKLIST)


async def build_brief(entry: CatalogOpportunity) -> tuple[list[str], list[str]]:
    """LLM-саммари/чеклист, с детерминированным фоллбэком, если LLM недоступен."""
    settings = get_settings()
    if settings.llm_configured:
        try:
            from llm.client import LLMClient

            data, _raw = await LLMClient().summarize_opportunity(
                title=entry.title,
                opp_type=entry.opportunity_type,
                description=entry.description,
                requirements=entry.requirements,
                deadline=entry.deadline,
            )
            if data:
                summary = data.get("summary")
                checklist = data.get("checklist")
                if isinstance(summary, list) and summary and isinstance(checklist, list) and checklist:
                    return [str(s) for s in summary][:4], [str(c) for c in checklist][:8]
        except Exception as exc:
            logger.warning("AI brief generation failed for catalog_id=%s: %s", entry.id, exc)

    return _heuristic_summary(entry), _heuristic_checklist(entry)


async def get_or_build_brief(session: AsyncSession, entry: CatalogOpportunity) -> dict:
    """Возвращает {"summary": [...], "checklist": [...]}, кэшируя на entry при первом вызове."""
    summary = _parse_list(entry.ai_summary_json)
    checklist = _parse_list(entry.requirements_checklist_json)
    if summary and checklist:
        return {"summary": summary, "checklist": checklist}

    summary, checklist = await build_brief(entry)
    entry.ai_summary_json = json.dumps(summary, ensure_ascii=False)
    entry.requirements_checklist_json = json.dumps(checklist, ensure_ascii=False)
    session.add(entry)
    await session.commit()
    return {"summary": summary, "checklist": checklist}

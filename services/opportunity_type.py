"""Participant vs audience (зритель) — refine LLM types from post text."""

from __future__ import annotations

import re

from llm.json_utils import coerce_llm_dict

STANDARD_TYPES = (
    "грант",
    "стипендия",
    "хакатон",
    "стажировка",
    "конкурс",
    "олимпиада",
    "эссе",
    "кейс",
    "летняя_школа",
    "курс",
    "мероприятие",
    "зритель",
    "другое",
)

_VIEWER_MARKERS = (
    "для зрителей",
    "для зрител",
    "зрителям",
    "зрител",
    "как зрител",
    "приходите посмотреть",
    "приглашаем зрит",
    "регистрация зрит",
    "наблюдател",
    "audience",
    "spectator",
    "as a viewer",
    "для аудитор",
)

_OPEN_PARTICIPANT_MARKERS = (
    "подать заяв",
    "прием заяв",
    "приём заяв",
    "приём заявок",
    "прием заявок",
    "открыт набор",
    "набор участник",
    "принимаются заяв",
    "принимаем заяв",
    "регистрация участник",
    "apply now",
    "register your startup",
    "подайте заяв",
    "участвуй",
    "участвовать в конкурс",
)

_CLOSED_EVENT_PATTERNS = (
    re.compile(r"\d+\s+стартап.{0,40}представ", re.I),
    re.compile(r"финал.{0,80}стартап", re.I),
    re.compile(r"победител.{0,30}получ", re.I),
    re.compile(r"отобранн.{0,30}стартап", re.I),
    re.compile(r"selected startups", re.I),
    re.compile(r"finalists", re.I),
)

_STARTUP_PITCH_MARKERS = (
    "startup battle",
    "стартап battle",
    "стартап-батл",
    "стартап батл",
    "pitch battle",
    "pitch day",
    "demo day",
    "launchzone",
    "launch zone",
    "питчинг",
    "pitching",
)

_STARTUP_SIGNALS = (
    "стартап",
    "startup",
    "стартапер",
    "founder",
    "фаундер",
    "питч",
    "pitch",
    "акселератор",
    "accelerator",
    "инкубатор",
    "incubator",
)


def _lower(text: str | None) -> str:
    return (text or "").lower()


def is_viewer_or_audience_event(text: str) -> bool:
    """Post is mainly about attending as audience, not competing/applying."""
    if not text or len(text.strip()) < 20:
        return False

    lowered = _lower(text)
    has_viewer = any(marker in lowered for marker in _VIEWER_MARKERS)
    has_open = any(marker in lowered for marker in _OPEN_PARTICIPANT_MARKERS)
    is_closed = any(p.search(text) for p in _CLOSED_EVENT_PATTERNS)

    if has_viewer and not has_open:
        return True
    if is_closed and has_viewer:
        return True
    if is_closed and not has_open:
        return True
    return False


def is_startup_pitch_competition(text: str) -> bool:
    """Startup pitch / battle / demo day — not a generic school contest."""
    if not text or len(text.strip()) < 15:
        return False
    lowered = _lower(text)
    has_startup = any(marker in lowered for marker in _STARTUP_SIGNALS)
    has_pitch_event = any(marker in lowered for marker in _STARTUP_PITCH_MARKERS)
    has_battle = bool(re.search(r"\bbattle\b", lowered)) and has_startup
    return has_pitch_event or has_battle


def refine_opportunity_type(source_text: str, llm_type: str | None, data: dict | None = None) -> str:
    """Map misclassified competition posts to зритель or хакатон when appropriate."""
    data = coerce_llm_dict(data) or {}
    base = (llm_type or data.get("type") or "другое").lower().strip()
    if base not in STANDARD_TYPES:
        base = "другое"

    if is_viewer_or_audience_event(source_text):
        return "зритель"

    if is_startup_pitch_competition(source_text) and base in ("конкурс", "мероприятие", "другое"):
        return "хакатон"

    return base


def normalize_catalog_type(raw: str | None) -> str:
    t = (raw or "другое").lower().strip()
    return t if t in STANDARD_TYPES else "другое"

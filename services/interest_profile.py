"""Разбор профиля интересов: типы, сферы, формат (онлайн/офлайн)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from services.interest_domains import (
    extract_domains_from_text,
    merge_approved_domains,
    suggest_unknown_domains,
)
from services.interest_matcher import extract_categories_from_text, is_standard_category


@dataclass
class InterestProfile:
    types: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    formats: list[str] = field(default_factory=list)
    unknown_domains: list[str] = field(default_factory=list)
    admin_questions: list[str] = field(default_factory=list)

    def all_categories(self) -> list[str]:
        merged: list[str] = []
        for item in [*self.types, *self.domains]:
            if item not in merged:
                merged.append(item)
        return merged[:8]

    def preferences_json(self) -> str:
        return json.dumps({"formats": self.formats}, ensure_ascii=False)


def extract_format_preferences(text: str) -> list[str]:
    lowered = (text or "").lower()
    formats: list[str] = []
    online_markers = (
        "онлайн",
        "online",
        "дистанц",
        "remote",
        "удалён",
        "удален",
        "virtual",
        "zoom",
    )
    offline_markers = (
        "офлайн",
        "offline",
        "оффлайн",
        "очно",
        "очный",
        "очная",
        "offline",
        "на месте",
    )
    if any(m in lowered for m in online_markers):
        formats.append("online")
    if any(m in lowered for m in offline_markers):
        formats.append("offline")
    return formats


def _is_broad_query(text: str) -> bool:
    return is_vague_or_unsure_interest(text)


_VAGUE_INTEREST_PATTERNS: tuple[str, ...] = (
    "интересует все",
    "интересует всё",
    "интересуюсь всем",
    "интересуюсь всём",
    "интересно все",
    "интересно всё",
    "всё что",
    "все что",
    "всё возмож",
    "все возмож",
    "любые возмож",
    "любую возмож",
    "любые",
    "без разницы",
    "что угодно",
    "что возможно",
    "ищу все",
    "ищу всё",
    "хочу все",
    "хочу всё",
    "не знаю чего",
    "не знаю что",
    "не знаю че ",
    "не знаю,",
    "не знаю.",
    "не знаю что искать",
    "не знаю что хочу",
    "не знаю чего хочу",
    "не определился",
    "не определилась",
    "не определились",
    "посоветуй",
    "посоветуйте",
    "порекоменду",
    "рекоменда",
    "рекомендуй",
    "что посовет",
    "что порекомен",
    "что послуш",
    "подскажи",
    "подскажите",
    "помогите найти",
    "помоги найти",
    "help me find",
    "any opportunities",
    "anything",
    "everything",
)


def is_vague_or_unsure_interest(text: str) -> bool:
    """Школьник не знает чего хочет или просит рекомендации."""
    lowered = (text or "").lower().strip()
    if not lowered:
        return False
    if any(p in lowered for p in _VAGUE_INTEREST_PATTERNS):
        return True
    if re.search(r"\bне\s+знаю\b", lowered) and not re.search(
        r"(грант|стипенди|хакатон|стажиров|конкурс|олимпиад|курс|меропри)", lowered
    ):
        return True
    return False


def apply_interest_defaults(profile: InterestProfile, text: str) -> None:
    """
    Размытый запрос → только «конкурс» (для школьников это универсальная категория).
    Пустой тип без явных ключевых слов → тоже «конкурс».
    """
    vague = is_vague_or_unsure_interest(text)
    if vague:
        profile.types = ["конкурс"]
        return
    if not profile.types:
        profile.types = ["конкурс"]


def _build_admin_questions(text: str, profile: InterestProfile) -> list[str]:
    """Admin review disabled — no questions sent to Telegram."""
    return []


def parse_format_preferences(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            formats = data.get("formats")
            if isinstance(formats, list):
                return [str(x).lower() for x in formats if x]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def parse_interest_profile(
    text: str,
    *,
    approved_domains: list[str] | None = None,
    apply_defaults: bool = True,
) -> InterestProfile:
    raw_categories = extract_categories_from_text(text)
    types = [c for c in raw_categories if is_standard_category(c)]
    domains = merge_approved_domains(extract_domains_from_text(text), approved_domains or [])

    for cat in raw_categories:
        if not is_standard_category(cat) and cat not in domains:
            if cat not in types:
                domains.append(cat)

    formats = extract_format_preferences(text)
    unknown = suggest_unknown_domains(text, approved=approved_domains)
    profile = InterestProfile(
        types=types,
        domains=domains,
        formats=formats,
        unknown_domains=unknown,
    )
    profile.admin_questions = _build_admin_questions(text, profile)
    if apply_defaults:
        apply_interest_defaults(profile, text)
    return profile

"""Serialize and dedupe catalog entries for the Telegram Mini App API."""

from __future__ import annotations

import re

from datetime import timezone

from db.models import CatalogOpportunity
from llm.deadline import parse_deadline
from services.catalog_dedup import catalog_dedupe_keys
from services.catalog_freshness import is_unknown_deadline, message_posted_at
from services.interest_matcher import (
    CATEGORY_DISPLAY,
    OPPORTUNITY_TYPES,
    entry_all_tags,
    extract_categories_from_text,
    relevance_score,
    resolve_catalog_types,
)
from services.opportunity_links import (
    normalize_application_url,
    normalize_message_link,
    pick_telegram_post_link,
)

CATEGORY_ORDER = (
    "грант",
    "стипендия",
    "хакатон",
    "стажировка",
    "конкурс",
    "мероприятие",
    "зритель",
)


def clean_source_name(name: str | None) -> str:
    if not name:
        return ""
    if "startup-course" in name.lower():
        return "Startup Course"
    cleaned = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", " ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or name.strip()


def serialize_tag(tag: str) -> dict:
    if tag in CATEGORY_DISPLAY:
        emoji, label = CATEGORY_DISPLAY[tag]
        return {"type": tag, "emoji": emoji, "label": label, "custom": False}
    return {"type": tag, "emoji": "🎯", "label": tag.capitalize(), "custom": True}


def serialize_opportunity(entry: CatalogOpportunity) -> dict:
    all_tags = entry_all_tags(entry)
    tag_objects = [serialize_tag(t) for t in all_tags]
    opp_type = entry.opportunity_type
    primary = tag_objects[0] if tag_objects else serialize_tag(opp_type)
    emoji, label = CATEGORY_DISPLAY.get(opp_type, ("📌", opp_type.capitalize()))
    app_url = normalize_application_url(entry.application_url)
    msg_link = pick_telegram_post_link(entry.message_link, entry.application_url)
    if not msg_link:
        msg_link = normalize_message_link(entry.message_link)
    return {
        "id": entry.id,
        "type": opp_type,
        "emoji": primary.get("emoji") or emoji,
        "label": primary.get("label") or label,
        "tags": tag_objects,
        "title": entry.title,
        "description": entry.description,
        "deadline": entry.deadline,
        "sourceChannelName": clean_source_name(entry.source_channel_name),
        "requirements": entry.requirements,
        "applicationUrl": app_url,
        "messageLink": msg_link,
        "isPremium": bool(app_url),
    }


def _entry_anchor_date(entry: CatalogOpportunity):
    posted = message_posted_at(entry)
    return posted.date() if posted else None


def sort_opportunities_by_deadline(entries: list[CatalogOpportunity]) -> list[CatalogOpportunity]:
    """Soonest deadline first; entries without a date follow, newest classified first."""

    def sort_key(entry: CatalogOpportunity) -> tuple[int, float, float]:
        anchor = _entry_anchor_date(entry)
        parsed = parse_deadline(entry.deadline, anchor_date=anchor)
        if parsed is not None:
            return (0, float(parsed.toordinal()), 0.0)
        classified = entry.classified_at
        if classified is None:
            ts = 0.0
        else:
            if classified.tzinfo is None:
                classified = classified.replace(tzinfo=timezone.utc)
            ts = classified.timestamp()
        return (1, 0.0, -ts)

    return sorted(entries, key=sort_key)


def dedupe_opportunities(entries: list[CatalogOpportunity]) -> list[CatalogOpportunity]:
    seen_keys: set[str] = set()
    unique: list[CatalogOpportunity] = []
    for entry in entries:
        keys = catalog_dedupe_keys(entry.title, entry.application_url, entry.description)
        if keys and keys & seen_keys:
            continue
        if keys:
            seen_keys |= keys
        unique.append(entry)
    return unique


def category_chips(categories: list[str]) -> list[dict]:
    chips = []
    for opp_type in categories:
        if opp_type in CATEGORY_DISPLAY:
            emoji, label = CATEGORY_DISPLAY[opp_type]
        else:
            emoji, label = "🎯", opp_type.capitalize()
        chips.append({"type": opp_type, "emoji": emoji, "label": label})
    return chips


MATCH_MIN_SCORE = 2.0

SEARCH_SUGGESTIONS = [
    {"emoji": "🚀", "text": "Я стартапер. Ищу питчи, хакатоны и гранты для стартапов в Казахстане"},
    {"emoji": "🎓", "text": "Стипендии за рубежом для магистратуры"},
    {"emoji": "💻", "text": "IT-стажировки и хакатоны для разработчиков"},
    {"emoji": "🏆", "text": "Конкурсы и олимпиады для школьников"},
]


def build_category_list(counts: dict[str, int], *, total_entries: int | None = None) -> list[dict]:
    total = total_entries if total_entries is not None else sum(counts.values())
    categories = [{"type": "all", "emoji": "✨", "label": "Все", "count": total}]
    seen: set[str] = set()
    for opp_type in CATEGORY_ORDER:
        count = counts.get(opp_type, 0)
        if count:
            emoji, label = CATEGORY_DISPLAY[opp_type]
            categories.append({"type": opp_type, "emoji": emoji, "label": label, "count": count})
            seen.add(opp_type)
    for tag in sorted(counts):
        if tag in seen or tag == "другое" or not counts[tag]:
            continue
        categories.append({"type": tag, "emoji": "🎯", "label": tag.capitalize(), "count": counts[tag]})
    return categories


def match_opportunities_for_user(
    interest_query: str,
    items: list[CatalogOpportunity],
    *,
    limit: int = 12,
    min_score: float | None = None,
) -> tuple[list[dict], list[str]]:
    text = interest_query.strip()
    categories = extract_categories_from_text(text)
    unique = dedupe_opportunities(items)
    floor = min_score if min_score is not None else MATCH_MIN_SCORE

    scored: list[tuple[float, CatalogOpportunity]] = []
    for entry in unique:
        score = relevance_score(text, entry)
        scored.append((score, entry))
    scored.sort(key=lambda pair: (pair[0], not is_unknown_deadline(pair[1].deadline)), reverse=True)

    picked = [entry for score, entry in scored if score >= floor][:limit]
    if not picked:
        intent = [c for c in categories if c in OPPORTUNITY_TYPES]
        if intent:
            wanted = set(intent)
            for _, entry in scored:
                if entry.opportunity_type in wanted or wanted & set(entry_all_tags(entry)):
                    picked.append(entry)
                    if len(picked) >= limit:
                        break
    return [serialize_opportunity(entry) for entry in picked], categories


def plural_opportunities(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "возможность"
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return "возможности"
    return "возможностей"

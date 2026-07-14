"""Serialize and dedupe catalog entries for the Telegram Mini App API."""

from __future__ import annotations

import re

from datetime import timezone

from db.models import CatalogOpportunity
from llm.deadline import parse_deadline
from services.catalog_dedup import catalog_dedupe_keys
from services.catalog_display import (
    entry_has_cash_prize,
    format_deadline_label,
    is_entry_new,
    sort_opportunities_by_newest,
)
from services.catalog_freshness import is_unknown_deadline, message_posted_at
from services.interest_matcher import (
    CATEGORY_DISPLAY,
    OPPORTUNITY_TYPES,
    entry_all_tags,
    entry_startup_related,
    extract_categories_from_text,
    is_domain_category,
    relevance_score,
    wants_startup_focus,
)
from services.match_feedback_memory import FeedbackHints, apply_feedback_score
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
    deadline_meta = format_deadline_label(entry.deadline, is_archived=not entry.is_active)
    cash_prize = entry_has_cash_prize(entry)
    classified = entry.classified_at
    if classified is not None and classified.tzinfo is None:
        classified = classified.replace(tzinfo=timezone.utc)
    return {
        "id": entry.id,
        "type": opp_type,
        "emoji": primary.get("emoji") or emoji,
        "label": primary.get("label") or label,
        "tags": tag_objects,
        "title": entry.title,
        "description": entry.description,
        "deadline": entry.deadline,
        "deadlineLabel": deadline_meta["label"],
        "deadlineUrgent": deadline_meta["urgent"],
        "hasCashPrize": cash_prize,
        "cashPrizeLabel": "Денежный приз" if cash_prize else "Без денежного приза",
        "isNew": is_entry_new(entry),
        "classifiedAt": classified.isoformat() if classified else None,
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


def _score_entries(
    text: str,
    entries: list[CatalogOpportunity],
    *,
    floor: float,
    feedback_hints: FeedbackHints | None,
) -> list[tuple[float, CatalogOpportunity]]:
    scored: list[tuple[float, CatalogOpportunity]] = []
    for entry in entries:
        adjusted = apply_feedback_score(relevance_score(text, entry), entry.id, feedback_hints)
        if adjusted is None or adjusted < floor:
            continue
        scored.append((adjusted, entry))
    scored.sort(key=lambda pair: (pair[0], not is_unknown_deadline(pair[1].deadline)), reverse=True)
    return scored


def _profile_domains(categories: list[str]) -> list[str]:
    return [category for category in categories if is_domain_category(category)]


def _entry_passes_domain_gate(
    text: str,
    entry: CatalogOpportunity,
    domains: list[str],
) -> bool:
    if not domains:
        return True
    blob = " ".join(
        filter(
            None,
            [
                entry.title,
                entry.description,
                entry.requirements,
                " ".join(entry_all_tags(entry)),
            ],
        )
    ).lower()
    if any(domain in blob for domain in domains):
        return True
    return relevance_score(text, entry) >= 5.0


def pick_opportunities_for_user(
    interest_query: str,
    items: list[CatalogOpportunity],
    *,
    limit: int = 12,
    min_score: float | None = None,
    feedback_hints: FeedbackHints | None = None,
) -> tuple[list[CatalogOpportunity], list[str]]:
    text = interest_query.strip()
    categories = extract_categories_from_text(text)
    unique = dedupe_opportunities(items)
    floor = min_score if min_score is not None else MATCH_MIN_SCORE
    profile_domains = _profile_domains(categories)

    intent_types = [c for c in categories if c in OPPORTUNITY_TYPES]
    extra_tags = [c for c in categories if c not in intent_types and c != "другое"]

    scored = _score_entries(text, unique, floor=floor, feedback_hints=feedback_hints)
    if profile_domains:
        scored = [
            (score, entry)
            for score, entry in scored
            if _entry_passes_domain_gate(text, entry, profile_domains)
        ]
    picked = [entry for _, entry in scored][:limit]

    if wants_startup_focus(categories, text):
        startup_scored = [
            (score, entry)
            for score, entry in scored
            if entry_startup_related(entry)
        ]
        if startup_scored:
            picked = [entry for _, entry in startup_scored[:limit]]

    if not picked and (intent_types or extra_tags) and not profile_domains:
        wanted = set(intent_types)
        extra = set(extra_tags)
        pool: list[CatalogOpportunity] = []
        for entry in unique:
            tags = set(entry_all_tags(entry))
            type_hit = bool(wanted) and (
                entry.opportunity_type in wanted or bool(wanted & tags)
            )
            extra_hit = bool(extra) and bool(extra & tags)
            if type_hit or extra_hit:
                pool.append(entry)
        if pool:
            pool_scored = _score_entries(text, pool, floor=floor, feedback_hints=feedback_hints)
            picked = [entry for _, entry in pool_scored][:limit]

    if not picked and intent_types and not profile_domains:
        wanted = set(intent_types)
        for entry in unique:
            if entry.id in (feedback_hints.user_negative_ids if feedback_hints else set()):
                continue
            if entry.opportunity_type in wanted or wanted & set(entry_all_tags(entry)):
                picked.append(entry)
                if len(picked) >= limit:
                    break

    return picked, categories


def match_opportunities_for_user(
    interest_query: str,
    items: list[CatalogOpportunity],
    *,
    limit: int = 12,
    min_score: float | None = None,
    feedback_hints: FeedbackHints | None = None,
) -> tuple[list[dict], list[str]]:
    picked, categories = pick_opportunities_for_user(
        interest_query,
        items,
        limit=limit,
        min_score=min_score,
        feedback_hints=feedback_hints,
    )
    return [serialize_opportunity(entry) for entry in picked], categories


async def match_opportunities_for_user_async(
    interest_query: str,
    items: list[CatalogOpportunity],
    *,
    limit: int = 12,
    min_score: float | None = None,
    feedback_hints: FeedbackHints | None = None,
) -> tuple[list[dict], list[str]]:
    picked, categories = pick_opportunities_for_user(
        interest_query,
        items,
        limit=max(limit * 3, limit),
        min_score=min_score,
        feedback_hints=feedback_hints,
    )
    if picked:
        from services.catalog_rerank import llm_rerank_catalog

        picked = await llm_rerank_catalog(interest_query, picked, max_pick=limit)
    return [serialize_opportunity(entry) for entry in picked], categories


def plural_opportunities(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "возможность"
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return "возможности"
    return "возможностей"

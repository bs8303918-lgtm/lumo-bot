"""Admin Mini App: список промптов интересов пользователей."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User
from db.repositories.opportunity_catalog import parse_interest_categories
from db.repositories.users import UserRepository
from services.interest_domains import display_for_domain
from services.interest_matcher import CATEGORY_DISPLAY, is_standard_category
from services.interest_profile import parse_format_preferences
from services.interest_stats import _user_categories, is_broad_interest

_FORMAT_LABELS = {
    "online": "Онлайн",
    "offline": "Офлайн",
}


def _tag_payload(key: str) -> dict:
    normalized = (key or "").lower().strip()
    if is_standard_category(normalized):
        emoji, label = CATEGORY_DISPLAY.get(normalized, ("•", normalized.capitalize()))
        return {"kind": "type", "key": normalized, "emoji": emoji, "label": label}
    emoji, label = display_for_domain(normalized)
    return {"kind": "domain", "key": normalized, "emoji": emoji, "label": label}


def _split_categories(categories: list[str]) -> tuple[list[dict], list[dict]]:
    types: list[dict] = []
    domains: list[dict] = []
    seen: set[str] = set()
    for raw in categories:
        key = (raw or "").lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        tag = _tag_payload(key)
        if tag["kind"] == "type":
            types.append(tag)
        else:
            domains.append(tag)
    return types, domains


def _serialize_user(user: User) -> dict:
    categories = _user_categories(user)
    types, domains = _split_categories(categories)
    formats = parse_format_preferences(user.interest_preferences_json)
    updated = user.updated_at or user.created_at
    return {
        "id": user.id,
        "username": user.username,
        "telegramId": user.telegram_id,
        "query": (user.interest_query or "").strip(),
        "types": types,
        "domains": domains,
        "formats": [
            {"key": fmt, "label": _FORMAT_LABELS.get(fmt, fmt)}
            for fmt in formats
        ],
        "isBroad": is_broad_interest(user),
        "updatedAt": updated.isoformat() if isinstance(updated, datetime) else None,
    }


def _category_summary(users: list[User]) -> list[dict]:
    counts: dict[str, int] = {}
    for user in users:
        if is_broad_interest(user):
            counts["__broad__"] = counts.get("__broad__", 0) + 1
            continue
        for cat in _user_categories(user):
            counts[cat] = counts.get(cat, 0) + 1
    rows: list[dict] = []
    for key, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        if key == "__broad__":
            rows.append(
                {
                    "key": "__broad__",
                    "emoji": "🌐",
                    "label": "Широкий запрос",
                    "count": count,
                }
            )
            continue
        tag = _tag_payload(key)
        rows.append(
            {
                "key": tag["key"],
                "emoji": tag["emoji"],
                "label": tag["label"],
                "count": count,
            }
        )
    return rows


def _matches_filter(user: User, *, search: str, category: str) -> bool:
    if category:
        if category == "__broad__":
            if not is_broad_interest(user):
                return False
        elif category not in _user_categories(user):
            return False

    if not search:
        return True

    needle = search.lower()
    haystacks = [
        (user.interest_query or "").lower(),
        (user.username or "").lower(),
        str(user.telegram_id),
        str(user.id),
    ]
    return any(needle in part for part in haystacks if part)


async def build_interest_prompts_dashboard(
    session: AsyncSession,
    *,
    search: str = "",
    category: str = "",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    users = await UserRepository(session).list_with_interests()
    search = (search or "").strip()
    category = (category or "").strip().lower()

    filtered = [u for u in users if _matches_filter(u, search=search, category=category)]
    total = len(filtered)
    page = filtered[offset : offset + limit]

    return {
        "total": total,
        "withInterest": len(users),
        "categorySummary": _category_summary(users),
        "items": [_serialize_user(user) for user in page],
    }

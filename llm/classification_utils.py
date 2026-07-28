"""Normalize LLM classification JSON into one or more catalog items."""

from __future__ import annotations

from typing import Any


def _pick_fields(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "is_opportunity": bool(source.get("is_opportunity")),
        "title": source.get("title"),
        "type": source.get("type"),
        "tags": source.get("tags"),
        "deadline": source.get("deadline"),
        "description": source.get("description"),
        "requirements": source.get("requirements"),
        "country": source.get("country"),
        "application_url": source.get("application_url"),
    }


def expand_classification_items(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    """
    Turn LLM JSON into 1..N catalog rows.

    Supports:
    - legacy single-object response
    - new ``opportunities`` array for roundup posts (several grants in one message)
    """
    if not data:
        return [{"is_opportunity": False}]

    if not data.get("is_opportunity"):
        return [_pick_fields(data)]

    opps = data.get("opportunities")
    if isinstance(opps, list):
        items: list[dict[str, Any]] = []
        for raw in opps:
            if not isinstance(raw, dict):
                continue
            merged = _pick_fields({**data, **raw, "is_opportunity": True})
            title = (merged.get("title") or "").strip()
            if not title or title in {"—", "-", "null"}:
                continue
            items.append(merged)
        if len(items) >= 2:
            return items
        if len(items) == 1:
            return items

    single = _pick_fields(data)
    title = (single.get("title") or "").strip()
    if single.get("is_opportunity") and title and title not in {"—", "-", "null"}:
        return [single]

    return [{"is_opportunity": False}]

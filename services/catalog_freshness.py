"""Filter stale catalog entries (especially posts without a deadline)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from config import get_settings
from db.models import CatalogOpportunity
from llm.deadline import (
    _EXPIRED_MARKERS,
    extract_dates_from_text,
    is_opportunity_expired,
    parse_deadline,
)
from services.message_freshness import message_post_date
from sqlalchemy.orm import attributes as orm_attributes


def _loaded_raw_message(entry: CatalogOpportunity):
    """Return raw_message only if already loaded — never trigger async lazy-load."""
    if "raw_message" in orm_attributes.instance_state(entry).unloaded:
        return None
    return entry.raw_message


def message_posted_at(entry: CatalogOpportunity) -> datetime | None:
    msg = _loaded_raw_message(entry)
    if msg is None:
        return None
    return message_post_date(msg)


def _entry_text(entry: CatalogOpportunity) -> str:
    text = entry.description or ""
    msg = _loaded_raw_message(entry)
    if msg and msg.text:
        text = f"{msg.text}\n{text}"
    return text


def is_unknown_deadline(deadline: str | None, *, anchor_date=None) -> bool:
    if not deadline:
        return True
    text = str(deadline).strip().lower()
    if text in _EXPIRED_MARKERS or text == "не указан":
        return True
    return parse_deadline(deadline, anchor_date=anchor_date) is None


def _entry_anchor_date(entry: CatalogOpportunity):
    posted = message_posted_at(entry)
    return posted.date() if posted else None


def is_catalog_entry_fresh(
    entry: CatalogOpportunity,
    *,
    max_age_days_no_deadline: int | None = None,
    max_post_age_days: int | None = None,
    now: datetime | None = None,
) -> bool:
    settings = get_settings()
    text = _entry_text(entry)
    anchor = _entry_anchor_date(entry)
    now = now or datetime.now(timezone.utc)
    today = now.date()

    no_deadline_days = max_age_days_no_deadline or settings.catalog_no_deadline_max_age_days
    post_age_limit = max_post_age_days or settings.monitor_initial_max_age_days

    posted = message_posted_at(entry)
    if posted is None:
        return False
    if posted < now - timedelta(days=post_age_limit):
        return False

    if is_opportunity_expired(entry.deadline, text, today=today, anchor_date=anchor):
        return False

    parsed = parse_deadline(entry.deadline, anchor_date=anchor) if entry.deadline else None
    if parsed is not None:
        return parsed >= today

    dates = extract_dates_from_text(text, today=today, for_expiry=True, anchor_date=anchor)
    if dates and max(dates) < today:
        return False

    return posted >= now - timedelta(days=no_deadline_days)


def filter_fresh_entries(
    entries: list[CatalogOpportunity],
    *,
    max_age_days_no_deadline: int | None = None,
    max_post_age_days: int | None = None,
) -> list[CatalogOpportunity]:
    return [
        entry
        for entry in entries
        if is_catalog_entry_fresh(
            entry,
            max_age_days_no_deadline=max_age_days_no_deadline,
            max_post_age_days=max_post_age_days,
        )
    ]

"""Filter catalog entries by deadline only (no post-age cutoffs)."""

from __future__ import annotations

from datetime import datetime, timezone

from db.models import CatalogOpportunity
from llm.deadline import _EXPIRED_MARKERS, parse_deadline
from services.message_freshness import message_post_date
from sqlalchemy.orm import attributes as orm_attributes


def _loaded_raw_message(entry: CatalogOpportunity):
    """Return raw_message only if already loaded — never trigger async lazy-load."""
    try:
        state = orm_attributes.instance_state(entry)
    except Exception:
        return getattr(entry, "raw_message", None)
    if "raw_message" in state.unloaded:
        return None
    return entry.raw_message


def message_posted_at(entry: CatalogOpportunity) -> datetime | None:
    msg = _loaded_raw_message(entry)
    if msg is None:
        return None
    return message_post_date(msg)


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


def is_catalog_deadline_expired(
    deadline: str | None,
    *,
    anchor_date=None,
    today=None,
) -> bool:
    """True only when an explicit parseable deadline is in the past.

    Unknown / missing deadlines are never treated as expired.
    """
    if not deadline:
        return False
    text = str(deadline).strip().lower()
    if text in _EXPIRED_MARKERS:
        return True
    if text == "не указан":
        return False
    today = today or datetime.now(timezone.utc).date()
    parsed = parse_deadline(deadline, anchor_date=anchor_date)
    if parsed is None:
        return False
    return parsed < today


def is_catalog_entry_fresh(
    entry: CatalogOpportunity,
    *,
    max_age_days_no_deadline: int | None = None,
    max_post_age_days: int | None = None,
    now: datetime | None = None,
) -> bool:
    """Catalog entries stay visible while is_active, unless their deadline has passed."""
    del max_age_days_no_deadline, max_post_age_days, now
    anchor = _entry_anchor_date(entry)
    return not is_catalog_deadline_expired(entry.deadline, anchor_date=anchor)


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

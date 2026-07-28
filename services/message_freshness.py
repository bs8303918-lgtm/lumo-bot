"""Recency checks for channel posts."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from config import get_settings
from db.models import RawMessage


def monitor_max_message_age_days() -> int:
    return get_settings().monitor_initial_max_age_days


def llm_max_message_age_days() -> int:
    return get_settings().llm_max_message_age_days


def catalog_no_deadline_max_age_days() -> int:
    return get_settings().catalog_no_deadline_max_age_days


def message_post_date(msg: RawMessage) -> datetime | None:
    """Real Telegram publish time — never use fetched_at as a proxy."""
    posted = msg.posted_at
    if posted is None:
        return None
    if posted.tzinfo is None:
        return posted.replace(tzinfo=timezone.utc)
    return posted


def message_reference_time(msg: RawMessage) -> datetime | None:
    return message_post_date(msg)


def is_message_older_than(msg: RawMessage, *, max_age_days: int) -> bool:
    ref = message_reference_time(msg)
    if ref is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    return ref < cutoff


def is_raw_message_too_old(msg: RawMessage, *, max_age_days: int | None = None) -> bool:
    days = max_age_days if max_age_days is not None else monitor_max_message_age_days()
    return is_message_older_than(msg, max_age_days=days)


def llm_classify_max_age_days() -> int:
    return get_settings().llm_classify_max_age_days


def is_raw_message_too_old_for_llm(msg: RawMessage) -> bool:
    return is_message_older_than(msg, max_age_days=llm_classify_max_age_days())


def raw_message_anchor_date(msg: RawMessage) -> date | None:
    ref = message_reference_time(msg)
    return ref.date() if ref else None

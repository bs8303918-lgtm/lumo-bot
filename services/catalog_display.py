"""Display helpers for catalog cards (deadlines, prizes, freshness)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from db.models import CatalogOpportunity
from llm.deadline import resolve_entry_deadline
from services.catalog_freshness import message_posted_at
from services.message_freshness import raw_message_anchor_date
from services.interest_matcher import _entry_has_cash_prize

_RU_MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

_EMPTY = frozenset({"", "—", "-", "null", "none", "n/a", "не указан"})
_DATE_RE = re.compile(r"^(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?$")

NEW_ENTRY_DAYS = 7


def _plural_days(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "день"
    if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return "дня"
    return "дней"


def _parse_display_date(text: str) -> date | None:
    match = _DATE_RE.match(text.strip())
    if not match:
        return None
    day, month = int(match.group(1)), int(match.group(2))
    if month < 1 or month > 12:
        return None
    year_raw = match.group(3)
    year = int(year_raw) if year_raw else date.today().year
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def format_deadline_label(deadline: str | None, *, is_archived: bool = False) -> dict:
    text = (deadline or "").strip()
    lower = text.lower()

    if not text or lower in _EMPTY:
        label = "В архиве" if is_archived else "не указан"
        return {"label": label, "urgent": False}

    if is_archived:
        parsed = _parse_display_date(text)
        if parsed:
            return {"label": f"Завершено · {parsed.strftime('%d.%m.%Y')}", "urgent": False}
        return {"label": f"В архиве · {text}", "urgent": False}

    if lower in {"ongoing", "открыт", "открыта", "open"}:
        return {"label": "Открыт набор", "urgent": False}

    days_match = re.search(r"(\d+)\s*дн", text, re.I)
    if days_match:
        days = int(days_match.group(1))
        if days <= 7:
            return {"label": f"Осталось {days} {_plural_days(days)}", "urgent": True}

    parsed = _parse_display_date(text)
    if parsed:
        today = date.today()
        diff = (parsed - today).days
        if 0 <= diff <= 7:
            return {"label": f"Осталось {diff} {_plural_days(diff)}", "urgent": True}
        return {"label": parsed.strftime("%d.%m.%Y"), "urgent": False}

    if "остал" in lower:
        return {"label": text, "urgent": True}

    return {"label": text, "urgent": False}


def entry_resolved_deadline(entry: CatalogOpportunity) -> str:
    anchor = None
    raw = getattr(entry, "raw_message", None)
    if raw is not None:
        anchor = raw_message_anchor_date(raw)
    return resolve_entry_deadline(
        entry.deadline,
        title=entry.title or "",
        description=entry.description or "",
        requirements=entry.requirements or "",
        anchor_date=anchor,
    )


def format_entry_deadline_label(entry: CatalogOpportunity, *, is_archived: bool = False) -> dict:
    return format_deadline_label(entry_resolved_deadline(entry), is_archived=is_archived)


def entry_text_blob(entry: CatalogOpportunity) -> str:
    return " ".join(
        filter(
            None,
            [
                entry.title or "",
                entry.description or "",
                entry.requirements or "",
            ],
        )
    )


def entry_has_cash_prize(entry: CatalogOpportunity) -> bool:
    return _entry_has_cash_prize(entry_text_blob(entry))


def entry_classified_at(entry: CatalogOpportunity) -> datetime | None:
    classified = entry.classified_at
    if classified is not None:
        if classified.tzinfo is None:
            return classified.replace(tzinfo=timezone.utc)
        return classified
    posted = message_posted_at(entry)
    if posted is None:
        return None
    if posted.tzinfo is None:
        return posted.replace(tzinfo=timezone.utc)
    return posted


def is_entry_new(entry: CatalogOpportunity, *, days: int = NEW_ENTRY_DAYS) -> bool:
    ts = entry_classified_at(entry)
    if ts is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return ts >= cutoff


def sort_opportunities_by_newest(entries: list[CatalogOpportunity]) -> list[CatalogOpportunity]:
    def sort_key(entry: CatalogOpportunity) -> float:
        ts = entry_classified_at(entry)
        return ts.timestamp() if ts else 0.0

    return sorted(entries, key=sort_key, reverse=True)

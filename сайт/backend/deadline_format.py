"""Human-readable deadline labels for the demo site (RU)."""

from __future__ import annotations

import re
from datetime import date

_RU_MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)

_EMPTY = frozenset({"", "—", "-", "null", "none", "n/a", "не указан"})
_DATE_RE = re.compile(r"^(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?$")


def _plural_days(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "день"
    if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return "дня"
    return "дней"


def _parse_date(text: str) -> date | None:
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
        label = "В архиве" if is_archived else "Без дедлайна"
        return {"label": label, "urgent": False}

    if is_archived:
        parsed = _parse_date(text)
        if parsed:
            return {"label": f"Завершено · {parsed.strftime('%d.%m.%Y')}", "urgent": False}
        if lower in {"ongoing", "открыт", "открыта", "open"}:
            return {"label": "В архиве", "urgent": False}
        return {"label": f"В архиве · {text}", "urgent": False}

    if lower in {"ongoing", "открыт", "открыта", "open"}:
        return {"label": "Открыт набор", "urgent": False}

    days_match = re.search(r"(\d+)\s*дн", text, re.I)
    if days_match:
        days = int(days_match.group(1))
        if days <= 7:
            return {"label": f"Осталось {days} {_plural_days(days)}", "urgent": True}

    parsed = _parse_date(text)
    if parsed:
        today = date.today()
        diff = (parsed - today).days
        if 0 <= diff <= 7:
            return {"label": f"Осталось {diff} {_plural_days(diff)}", "urgent": True}
        return {"label": f"{parsed.day} {_RU_MONTHS[parsed.month - 1]}", "urgent": False}

    if "остал" in lower:
        return {"label": text, "urgent": True}

    return {"label": text, "urgent": False}

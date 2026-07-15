import re
from datetime import date

_EXPIRED_MARKERS = (
    "не указан",
    "null",
    "none",
    "n/a",
    "-",
    "",
)

_DATE_RE = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{2,4})\b")
_DOT_RANGE_RE = re.compile(r"\b(\d{1,2})-(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?\b")
_SHORT_DOT_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})(?!\.)\b")

_RU_MONTHS = {
    "января": 1, "январь": 1, "февраля": 2, "февраль": 2,
    "марта": 3, "март": 3, "апреля": 4, "апрель": 4,
    "мая": 5, "май": 5, "июня": 6, "июнь": 6,
    "июля": 7, "июль": 7, "августа": 8, "август": 8,
    "сентября": 9, "сентябрь": 9, "октября": 10, "октябрь": 10,
    "ноября": 11, "ноябрь": 11, "декабря": 12, "декабрь": 12,
}

_EN_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}

_KZ_MONTHS = {
    "қаңтар": 1, "ақпан": 2, "наурыз": 3, "сәуір": 4, "мамыр": 5, "маусым": 6,
    "шілде": 7, "тамыз": 8, "қыркүйек": 9, "қазан": 10, "қараша": 11, "желтоқсан": 12,
}

_RU_MONTH_PATTERN = "|".join(sorted(_RU_MONTHS.keys(), key=len, reverse=True))
_EN_MONTH_PATTERN = "|".join(sorted(_EN_MONTHS.keys(), key=len, reverse=True))
_KZ_MONTH_PATTERN = "|".join(sorted(_KZ_MONTHS.keys(), key=len, reverse=True))

_CROSS_MONTH_RANGE_RE = re.compile(
    r"\b(\d{1,2})[./](\d{1,2})\s*[–—-]\s*(\d{1,2})[./](\d{1,2})\b"
)
_RANGE_RU_RE = re.compile(
    rf"(\d{{1,2}})\s*(?:-|–|—)\s*(\d{{1,2}})\s+({_RU_MONTH_PATTERN})(?:\s+(\d{{4}}))?",
    re.IGNORECASE,
)
_SINGLE_RU_RE = re.compile(
    rf"(\d{{1,2}})\s+({_RU_MONTH_PATTERN})(?:\s+(\d{{4}}))?",
    re.IGNORECASE,
)
_SINGLE_EN_RE = re.compile(
    rf"(\d{{1,2}})\s+({_EN_MONTH_PATTERN})(?:\s+(\d{{4}}))?",
    re.IGNORECASE,
)
_SINGLE_KZ_RE = re.compile(
    rf"(\d{{1,2}})\s+({_KZ_MONTH_PATTERN})(?:\s+(\d{{4}}))?",
    re.IGNORECASE,
)


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _infer_year(
    month: int,
    day: int,
    today: date,
    explicit_year: int | None,
    *,
    for_expiry: bool = False,
    anchor_date: date | None = None,
) -> int:
    if explicit_year:
        return explicit_year if explicit_year > 99 else explicit_year + 2000
    ref = anchor_date if (for_expiry and anchor_date) else today
    if for_expiry:
        this_year = _safe_date(ref.year, month, day)
        if this_year and this_year >= ref:
            return ref.year
        next_year = _safe_date(ref.year + 1, month, day)
        if next_year and next_year >= ref:
            return ref.year + 1
        return ref.year
    candidate = _safe_date(today.year, month, day)
    if candidate and candidate >= today:
        return today.year
    return today.year + 1


def _parse_named_month_day(
    day: int,
    month_name: str,
    year_str: str | None,
    months: dict[str, int],
    today: date,
    *,
    for_expiry: bool = False,
    anchor_date: date | None = None,
) -> date | None:
    month = months.get(month_name.lower())
    if not month:
        return None
    year = int(year_str) if year_str else _infer_year(
        month, day, today, None, for_expiry=for_expiry, anchor_date=anchor_date
    )
    if year < 100:
        year += 2000
    return _safe_date(year, month, day)


def _collect_named_month_dates(
    text: str,
    regex: re.Pattern[str],
    months: dict[str, int],
    today: date,
    *,
    for_expiry: bool = False,
    anchor_date: date | None = None,
) -> list[date]:
    found: list[date] = []
    for match in regex.finditer(text):
        parsed = _parse_named_month_day(
            int(match.group(1)),
            match.group(2),
            match.group(3),
            months,
            today,
            for_expiry=for_expiry,
            anchor_date=anchor_date,
        )
        if parsed:
            found.append(parsed)
    return found


def _parse_cross_month_range(
    value: str,
    today: date,
    *,
    for_expiry: bool = True,
    anchor_date: date | None = None,
) -> date | None:
    match = _CROSS_MONTH_RANGE_RE.search(value)
    if not match:
        return None
    end_day, end_month = int(match.group(3)), int(match.group(4))
    if end_month > 12:
        return None
    year = _infer_year(
        end_month, end_day, today, None, for_expiry=for_expiry, anchor_date=anchor_date
    )
    return _safe_date(year, end_month, end_day)


def is_missing_deadline(value: str | None) -> bool:
    text = (value or "").strip().lower()
    return not text or text in _EXPIRED_MARKERS


def infer_deadline_from_text(
    text: str,
    *,
    anchor_date: date | None = None,
) -> str | None:
    """Извлечь дату из текста поста (часто «08.08» в начале строки)."""
    if not (text or "").strip():
        return None
    for chunk in text.split("\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parsed = parse_deadline(chunk, anchor_date=anchor_date)
        if parsed:
            return parsed.strftime("%d.%m.%Y")
    parsed = parse_deadline(text, anchor_date=anchor_date)
    if parsed:
        return parsed.strftime("%d.%m.%Y")
    latest = latest_date_in_text(text, for_expiry=True, anchor_date=anchor_date)
    if latest:
        return latest.strftime("%d.%m.%Y")
    return None


def resolve_entry_deadline(
    deadline: str | None,
    *,
    title: str = "",
    description: str = "",
    requirements: str = "",
    anchor_date: date | None = None,
) -> str:
    text = (deadline or "").strip()
    if not is_missing_deadline(text) and parse_deadline(text, anchor_date=anchor_date):
        return text
    blob = "\n".join(filter(None, [description, title, requirements]))
    inferred = infer_deadline_from_text(blob, anchor_date=anchor_date)
    if inferred:
        return inferred
    return text or "не указан"


def parse_deadline(value: str | None, *, anchor_date: date | None = None) -> date | None:
    if not value:
        return None
    text = str(value).strip().lower()
    if text in _EXPIRED_MARKERS:
        return None

    match = _DATE_RE.search(str(value))
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if year < 100:
            year += 2000
        return _safe_date(year, month, day)

    today = date.today()

    cross = _parse_cross_month_range(str(value), today, for_expiry=True, anchor_date=anchor_date)
    if cross:
        return cross

    for match in _SHORT_DOT_RE.finditer(str(value)):
        day, month = int(match.group(1)), int(match.group(2))
        if month > 12:
            continue
        year = _infer_year(
            month, day, today, None, for_expiry=True, anchor_date=anchor_date
        )
        parsed = _safe_date(year, month, day)
        if parsed:
            return parsed

    for dates in (
        _collect_named_month_dates(
            str(value), _SINGLE_RU_RE, _RU_MONTHS, today, for_expiry=True, anchor_date=anchor_date
        ),
        _collect_named_month_dates(
            str(value), _SINGLE_EN_RE, _EN_MONTHS, today, for_expiry=True, anchor_date=anchor_date
        ),
        _collect_named_month_dates(
            str(value), _SINGLE_KZ_RE, _KZ_MONTHS, today, for_expiry=True, anchor_date=anchor_date
        ),
    ):
        if dates:
            return max(dates)
    return None


def extract_dates_from_text(
    text: str,
    *,
    today: date | None = None,
    for_expiry: bool = False,
    anchor_date: date | None = None,
) -> list[date]:
    today = today or date.today()
    found: list[date] = []

    for match in _DATE_RE.finditer(text):
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if year < 100:
            year += 2000
        parsed = _safe_date(year, month, day)
        if parsed:
            found.append(parsed)

    for match in _DOT_RANGE_RE.finditer(text):
        end_day = int(match.group(2))
        month = int(match.group(3))
        year = int(match.group(4)) if match.group(4) else _infer_year(
            month, end_day, today, None, for_expiry=for_expiry, anchor_date=anchor_date
        )
        if year < 100:
            year += 2000
        for day in (int(match.group(1)), end_day):
            parsed = _safe_date(year, month, day)
            if parsed:
                found.append(parsed)

    cross = _parse_cross_month_range(
        text, today, for_expiry=for_expiry, anchor_date=anchor_date
    )
    if cross:
        found.append(cross)

    for match in _SHORT_DOT_RE.finditer(text):
        day, month = int(match.group(1)), int(match.group(2))
        if month > 12:
            continue
        year = _infer_year(
            month, day, today, None, for_expiry=for_expiry, anchor_date=anchor_date
        )
        parsed = _safe_date(year, month, day)
        if parsed:
            found.append(parsed)

    for match in _RANGE_RU_RE.finditer(text):
        month = _RU_MONTHS[match.group(3).lower()]
        year = int(match.group(4)) if match.group(4) else _infer_year(
            month, int(match.group(2)), today, None, for_expiry=for_expiry, anchor_date=anchor_date
        )
        for day in (int(match.group(1)), int(match.group(2))):
            parsed = _safe_date(year, month, day)
            if parsed:
                found.append(parsed)

    found.extend(
        _collect_named_month_dates(
            text, _SINGLE_RU_RE, _RU_MONTHS, today, for_expiry=for_expiry, anchor_date=anchor_date
        )
    )
    found.extend(
        _collect_named_month_dates(
            text, _SINGLE_EN_RE, _EN_MONTHS, today, for_expiry=for_expiry, anchor_date=anchor_date
        )
    )
    found.extend(
        _collect_named_month_dates(
            text, _SINGLE_KZ_RE, _KZ_MONTHS, today, for_expiry=for_expiry, anchor_date=anchor_date
        )
    )

    return found


def latest_date_in_text(
    text: str,
    *,
    today: date | None = None,
    for_expiry: bool = False,
    anchor_date: date | None = None,
) -> date | None:
    dates = extract_dates_from_text(
        text, today=today, for_expiry=for_expiry, anchor_date=anchor_date
    )
    return max(dates) if dates else None


def is_deadline_expired(
    value: str | None,
    *,
    today: date | None = None,
    anchor_date: date | None = None,
) -> bool:
    parsed = parse_deadline(value, anchor_date=anchor_date)
    if parsed is None:
        return False
    today = today or date.today()
    return parsed < today


def is_opportunity_expired(
    deadline: str | None,
    message_text: str,
    *,
    today: date | None = None,
    anchor_date: date | None = None,
) -> bool:
    today = today or date.today()
    parsed_deadline = parse_deadline(deadline, anchor_date=anchor_date)
    if parsed_deadline is not None:
        return parsed_deadline < today

    latest_in_text = latest_date_in_text(
        message_text, today=today, for_expiry=True, anchor_date=anchor_date
    )
    if latest_in_text is None:
        return False
    return latest_in_text < today


def format_today() -> str:
    return date.today().strftime("%d.%m.%Y")

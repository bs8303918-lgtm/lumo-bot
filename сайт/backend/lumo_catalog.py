"""Read-only access to lumo-bot catalog_opportunities for the demo site."""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from deadline_format import format_deadline_label
from interest_match import extract_categories_from_text, relevance_score

_SELECT_FIELDS = """
    id, opportunity_type, title, deadline, description, requirements,
    application_url, source_channel_name, message_link, is_active
"""

ROOT = Path(__file__).resolve().parents[2]


def _resolve_db_path() -> Path:
    """Same database as lumo-bot: lumo-bot/lumo.db unless LUMO_DB is set."""
    override = os.environ.get("LUMO_DB") or os.environ.get("DATABASE_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return (ROOT / "lumo.db").resolve()


LUMO_DB = _resolve_db_path()

CATEGORY_DISPLAY: dict[str, tuple[str, str]] = {
    "грант": ("💰", "Гранты"),
    "стипендия": ("🎓", "Стипендии"),
    "хакатон": ("💻", "Хакатоны"),
    "стажировка": ("🏢", "Стажировки"),
    "конкурс": ("🏆", "Конкурсы"),
    "мероприятие": ("📅", "Мероприятия"),
}

CATEGORY_ORDER = (
    "грант",
    "стипендия",
    "хакатон",
    "стажировка",
    "конкурс",
    "мероприятие",
)


@dataclass
class _ScoredEntry:
    id: int
    row: sqlite3.Row
    title: str
    description: str
    requirements: str | None
    opportunity_type: str
    score: float = 0.0


def _connect() -> sqlite3.Connection:
    if not LUMO_DB.is_file():
        raise FileNotFoundError(f"Lumo database not found: {LUMO_DB}")
    conn = sqlite3.connect(LUMO_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _clean_source_name(name: str | None) -> str:
    if not name:
        return ""
    if "startup-course" in name.lower():
        return "Startup Course"
    cleaned = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", " ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or name.strip()


def _features(requirements: str | None, opp_type: str) -> list[str]:
    emoji, label = CATEGORY_DISPLAY.get(opp_type, ("📌", opp_type.capitalize()))
    items = [f"{emoji} {label}"]
    if requirements:
        for line in requirements.replace(";", "\n").splitlines():
            text = line.strip(" •-\t")
            if text and len(items) < 4:
                items.append(text)
    return items


def _serialize(row: sqlite3.Row) -> dict:
    opp_type = row["opportunity_type"]
    emoji, label = CATEGORY_DISPLAY.get(opp_type, ("📌", opp_type.capitalize()))
    requirements = row["requirements"]
    is_archived = not bool(row["is_active"])
    deadline_meta = format_deadline_label(row["deadline"], is_archived=is_archived)
    return {
        "id": row["id"],
        "type": opp_type,
        "emoji": emoji,
        "label": label,
        "title": row["title"],
        "description": row["description"],
        "deadline": row["deadline"],
        "deadlineLabel": deadline_meta["label"],
        "deadlineUrgent": deadline_meta["urgent"],
        "isArchived": is_archived,
        "sourceChannelName": _clean_source_name(row["source_channel_name"]),
        "requirements": requirements,
        "applicationUrl": row["application_url"],
        "messageLink": row["message_link"],
        "features": _features(requirements, opp_type),
        "isPremium": bool(row["application_url"]),
    }


def catalog_status() -> dict:
    if not LUMO_DB.is_file():
        return {
            "connected": False,
            "dbPath": str(LUMO_DB),
            "error": f"Файл базы не найден: {LUMO_DB}",
        }

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS archived
            FROM catalog_opportunities
            WHERE opportunity_type != 'другое'
            """
        ).fetchone()

    return {
        "connected": True,
        "dbPath": str(LUMO_DB),
        "total": int(row["total"] or 0),
        "active": int(row["active"] or 0),
        "archived": int(row["archived"] or 0),
    }


def list_categories() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT opportunity_type, COUNT(*) AS cnt
            FROM catalog_opportunities
            WHERE opportunity_type != 'другое'
            GROUP BY opportunity_type
            """
        ).fetchall()

    counts = {row["opportunity_type"]: row["cnt"] for row in rows}
    total = sum(counts.values())
    categories = [{"type": "all", "emoji": "✨", "label": "Все", "count": total}]
    for opp_type in CATEGORY_ORDER:
        count = counts.get(opp_type, 0)
        if count:
            emoji, label = CATEGORY_DISPLAY[opp_type]
            categories.append({"type": opp_type, "emoji": emoji, "label": label, "count": count})
    return categories


def _dedupe_rows(rows: list[sqlite3.Row]) -> list[sqlite3.Row]:
    seen_keys: set[str] = set()
    unique: list[sqlite3.Row] = []
    for row in rows:
        keys = _catalog_dedupe_keys(row["title"], row["application_url"], row["description"])
        if keys and keys & seen_keys:
            continue
        if keys:
            seen_keys |= keys
        unique.append(row)
    return unique


_GENERIC_TITLES = frozenset({"хакатон", "конкурс", "грант", "стипендия", "стажировка", "мероприятие", "возможность", "—", "-"})
_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)


def _normalize_title(title: str | None) -> str:
    if not title:
        return ""
    text = re.sub(r"\s+", " ", title.lower().strip())
    return text.strip("«»\"'")


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    text = url.strip()
    if not text:
        return None
    lower = text.lower()
    inner = lower.strip("[]()«»\"'")
    placeholders = {
        "—", "-", "none", "null", "n/a",
        "ссылка", "ссылка на регистрацию", "link", "registration link",
    }
    if lower in placeholders or inner in placeholders:
        return None
    if "://" not in lower and (" " in text or not any(ch in text for ch in ".:/")):
        return None
    if "://" in lower and ("[" in text or "]" in text):
        bracket_host = re.search(r"\[([^\]]+)\]", text)
        if bracket_host and (" " in bracket_host.group(1) or "." not in bracket_host.group(1)):
            return None
    try:
        if "://" not in text:
            if "." not in text:
                return None
            text = f"https://{text}"
        parsed = urlparse(text)
        if not parsed.netloc or " " in parsed.netloc:
            return None
        if not parsed.hostname or "." not in parsed.hostname:
            return None
        path = parsed.path.rstrip("/") or "/"
        return urlunparse((parsed.scheme or "https", parsed.netloc, path, "", "", ""))
    except ValueError:
        return None


def _catalog_dedupe_keys(title: str | None, application_url: str | None, description: str | None) -> set[str]:
    keys: set[str] = set()
    norm_title = _normalize_title(title)
    if len(norm_title) >= 8 and norm_title not in _GENERIC_TITLES:
        keys.add(f"title:{norm_title}")
    norm_app = _normalize_url(application_url)
    if norm_app:
        keys.add(f"url:{norm_app}")
    if description:
        for raw in _URL_RE.findall(description):
            norm = _normalize_url(raw.rstrip(".,;)"))
            if norm:
                keys.add(f"url:{norm}")
    return keys


def list_opportunities(
    *,
    category: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    clauses = ["opportunity_type != 'другое'"]
    params: list[object] = []

    if category and category != "all":
        clauses.append("opportunity_type = ?")
        params.append(category)

    if q:
        needle = f"%{q.strip().lower()}%"
        clauses.append(
            "(LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(source_channel_name) LIKE ?)"
        )
        params.extend([needle, needle, needle])

    where = " AND ".join(clauses)
    sql = f"""
        SELECT {_SELECT_FIELDS.strip()}
        FROM catalog_opportunities
        WHERE {where}
        ORDER BY is_active DESC, classified_at DESC
    """

    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    deduped = _dedupe_rows(rows)
    total = len(deduped)
    page = max(1, page)
    page_size = max(1, min(page_size, 50))
    start = (page - 1) * page_size
    page_rows = deduped[start : start + page_size]

    return {
        "items": [_serialize(row) for row in page_rows],
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


def get_opportunity(item_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT {_SELECT_FIELDS.strip()}
            FROM catalog_opportunities
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
    return _serialize(row) if row else None


def _category_chips(categories: list[str]) -> list[dict]:
    chips = []
    for opp_type in categories:
        emoji, label = CATEGORY_DISPLAY.get(opp_type, ("📌", opp_type.capitalize()))
        chips.append({"type": opp_type, "emoji": emoji, "label": label})
    return chips


def match_opportunities(query: str, *, limit: int = 12) -> dict:
    text = query.strip()
    if len(text) < 3:
        raise ValueError("Query too short")

    categories = extract_categories_from_text(text)
    placeholders = ",".join("?" for _ in categories)

    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT {_SELECT_FIELDS.strip()}
            FROM catalog_opportunities
            WHERE opportunity_type != 'другое'
              AND opportunity_type IN ({placeholders})
            ORDER BY is_active DESC, classified_at DESC
            LIMIT 400
            """,
            categories,
        ).fetchall()

    unique_rows = _dedupe_rows(rows)
    scored: list[_ScoredEntry] = []
    for row in unique_rows:
        entry = _ScoredEntry(
            id=row["id"],
            row=row,
            title=row["title"],
            description=row["description"],
            requirements=row["requirements"],
            opportunity_type=row["opportunity_type"],
        )
        entry.score = relevance_score(text, entry)
        scored.append(entry)

    scored.sort(key=lambda item: item.score, reverse=True)
    picked = [item for item in scored if item.score >= 1.0][:limit]
    if not picked:
        picked = scored[:limit]

    items = [_serialize(item.row) for item in picked]
    for item, entry in zip(items, picked, strict=True):
        item["matchScore"] = round(entry.score, 1)

    count = len(items)
    if count:
        message = f"Подобрал {count} {_plural_opportunities(count)} под твой запрос."
    else:
        message = "Пока не нашёл подходящего в базе — попробуй переформулировать запрос."

    return {
        "query": text,
        "categories": _category_chips(categories),
        "message": message,
        "items": items,
    }


def _plural_opportunities(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "возможность"
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return "возможности"
    return "возможностей"

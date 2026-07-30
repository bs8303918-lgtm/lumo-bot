"""Умные фильтры: формат (онлайн/офлайн), команда/соло — эвристики по тексту поста."""

from __future__ import annotations

from db.models import CatalogOpportunity

_ONLINE_MARKERS = ("онлайн", "online", "дистанц", "remote", "удалён", "удален", "virtual", "zoom")
_OFFLINE_MARKERS = ("офлайн", "offline", "оффлайн", "очно", "очный", "очная", "на месте", "в кампусе", "on-site", "onsite")

_TEAM_MARKERS = (
    "команд",
    "team of",
    "в команде",
    "team-based",
    "team project",
    "сформируй команду",
    "групп проект",
    "групповой проект",
)
_SOLO_MARKERS = (
    "индивидуальн",
    "соло",
    "individually",
    "individual participation",
    "личное участие",
    "один участник",
    "single participant",
)


def _blob(entry: CatalogOpportunity) -> str:
    return " ".join(filter(None, [entry.title, entry.description, entry.requirements or ""])).lower()


def entry_format(entry: CatalogOpportunity) -> str:
    """"online" | "offline" | "hybrid" | "unknown"."""
    blob = _blob(entry)
    has_online = any(m in blob for m in _ONLINE_MARKERS)
    has_offline = any(m in blob for m in _OFFLINE_MARKERS)
    if has_online and has_offline:
        return "hybrid"
    if has_online:
        return "online"
    if has_offline:
        return "offline"
    return "unknown"


def entry_team_requirement(entry: CatalogOpportunity) -> str:
    """"team" | "solo" | "unknown"."""
    blob = _blob(entry)
    has_team = any(m in blob for m in _TEAM_MARKERS)
    has_solo = any(m in blob for m in _SOLO_MARKERS)
    if has_team and not has_solo:
        return "team"
    if has_solo and not has_team:
        return "solo"
    return "unknown"


def matches_format_filter(entry: CatalogOpportunity, wanted: str) -> bool:
    if wanted in (None, "", "any"):
        return True
    fmt = entry_format(entry)
    if wanted == "online":
        return fmt in ("online", "hybrid")
    if wanted == "offline":
        return fmt in ("offline", "hybrid")
    return True


def matches_team_filter(entry: CatalogOpportunity, wanted: str) -> bool:
    if wanted in (None, "", "any"):
        return True
    requirement = entry_team_requirement(entry)
    if requirement == "unknown":
        return True
    return requirement == wanted

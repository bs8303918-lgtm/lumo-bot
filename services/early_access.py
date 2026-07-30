"""Premium: приоритетный доступ к новым конкурсам (публикуются на N часов раньше)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from config import get_settings
from db.models import CatalogOpportunity, User
from services.subscription import is_paid_plan_active


def _classified_at(entry: CatalogOpportunity) -> datetime | None:
    classified = entry.classified_at
    if classified is None:
        return None
    if classified.tzinfo is None:
        classified = classified.replace(tzinfo=timezone.utc)
    return classified


def is_in_early_access_window(entry: CatalogOpportunity, *, now: datetime | None = None) -> bool:
    settings = get_settings()
    hours = settings.premium_early_access_hours
    if hours <= 0:
        return False
    classified = _classified_at(entry)
    if classified is None:
        return False
    now = now or datetime.now(timezone.utc)
    return now - classified < timedelta(hours=hours)


def filter_for_early_access(
    entries: list[CatalogOpportunity],
    user: User,
    *,
    now: datetime | None = None,
) -> list[CatalogOpportunity]:
    """Скрыть от free-пользователей карточки, которые ещё в премиум-окне."""
    if is_paid_plan_active(user):
        return entries
    now = now or datetime.now(timezone.utc)
    return [e for e in entries if not is_in_early_access_window(e, now=now)]

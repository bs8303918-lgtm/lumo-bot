"""Premium: приоритетный доступ к новым конкурсам (публикуются на N часов раньше).

The cutoff must be applied as a SQL WHERE clause at the repository query level
(see visible_before= on CatalogRepository methods) — never as a Python-side
post-filter on an already-LIMITed page. The catalog feed queries only the top
N most-recently-classified rows; when the classification backlog produces a
burst of rows within the window (common — classification runs continuously),
a post-filter can strip 100% of that page even though older, still-valid
opportunities exist further back that the query never fetched.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from config import get_settings
from db.models import User
from services.subscription import is_paid_plan_active


def early_access_cutoff(user: User, *, now: datetime | None = None) -> datetime | None:
    """Timestamp to pass as visible_before=. None means no restriction (unlimited/paid/disabled)."""
    if is_paid_plan_active(user):
        return None
    settings = get_settings()
    hours = settings.premium_early_access_hours
    if hours <= 0:
        return None
    now = now or datetime.now(timezone.utc)
    return now - timedelta(hours=hours)

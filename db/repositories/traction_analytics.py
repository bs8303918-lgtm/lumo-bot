"""Click and view analytics for catalog traction (admin dashboard)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.event_types import (
    BUTTON_APPLY_CLICK,
    BUTTON_DETAILS_CLICK,
    CATALOG_APPLY_CLICK,
    CATALOG_TELEGRAM_CLICK,
    CATALOG_VIEW,
)
from db.models import CatalogOpportunity, Event, OpportunitySubmission, SentMatch, User


def _since(days: int | None) -> datetime | None:
    if not days or days <= 0:
        return None
    return datetime.now(timezone.utc) - timedelta(days=days)


def _event_filter_since(since: datetime | None):
    if since is None:
        return True
    return Event.created_at >= since


class TractionAnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _events_since(self, since: datetime | None, *event_types: str) -> list[Event]:
        stmt = select(Event).where(Event.event_type.in_(event_types))
        if since:
            stmt = stmt.where(Event.created_at >= since)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _match_catalog_map(self, match_ids: set[int]) -> dict[int, int]:
        if not match_ids:
            return {}
        result = await self.session.execute(
            select(SentMatch.id, CatalogOpportunity.id)
            .join(CatalogOpportunity, SentMatch.raw_message_id == CatalogOpportunity.raw_message_id)
            .where(SentMatch.id.in_(match_ids))
        )
        return {match_id: catalog_id for match_id, catalog_id in result.all()}

    async def _catalog_map(self, catalog_ids: set[int]) -> dict[int, CatalogOpportunity]:
        if not catalog_ids:
            return {}
        result = await self.session.execute(
            select(CatalogOpportunity).where(CatalogOpportunity.id.in_(catalog_ids))
        )
        return {row.id: row for row in result.scalars().all()}

    async def build_dashboard(self, *, days: int = 30, top_limit: int = 15) -> dict:
        since = _since(days)
        events = await self._events_since(
            since,
            CATALOG_VIEW,
            CATALOG_APPLY_CLICK,
            CATALOG_TELEGRAM_CLICK,
            BUTTON_APPLY_CLICK,
            BUTTON_DETAILS_CLICK,
        )

        item_stats: dict[int, dict] = {}
        summary = {
            "views": 0,
            "applyClicks": 0,
            "telegramClicks": 0,
            "uniqueUsers": set(),
            "botApply": 0,
            "botTelegram": 0,
            "appViews": 0,
            "appApply": 0,
            "appTelegram": 0,
        }

        def bucket(catalog_id: int) -> dict:
            if catalog_id not in item_stats:
                item_stats[catalog_id] = {
                    "catalogId": catalog_id,
                    "views": 0,
                    "applyClicks": 0,
                    "telegramClicks": 0,
                    "uniqueUsers": set(),
                }
            return item_stats[catalog_id]

        bot_match_ids = {
            event.related_id
            for event in events
            if event.event_type in (BUTTON_APPLY_CLICK, BUTTON_DETAILS_CLICK) and event.related_id
        }
        match_to_catalog = await self._match_catalog_map(bot_match_ids)

        for event in events:
            if event.user_id:
                summary["uniqueUsers"].add(event.user_id)

            catalog_id: int | None = None
            if event.event_type == CATALOG_VIEW:
                catalog_id = event.related_id
                summary["views"] += 1
                summary["appViews"] += 1
            elif event.event_type == CATALOG_APPLY_CLICK:
                catalog_id = event.related_id
                summary["applyClicks"] += 1
                summary["appApply"] += 1
            elif event.event_type == CATALOG_TELEGRAM_CLICK:
                catalog_id = event.related_id
                summary["telegramClicks"] += 1
                summary["appTelegram"] += 1
            elif event.event_type == BUTTON_APPLY_CLICK:
                summary["applyClicks"] += 1
                summary["botApply"] += 1
                catalog_id = match_to_catalog.get(event.related_id or 0)
            elif event.event_type == BUTTON_DETAILS_CLICK:
                summary["telegramClicks"] += 1
                summary["botTelegram"] += 1
                catalog_id = match_to_catalog.get(event.related_id or 0)

            if not catalog_id:
                continue

            row = bucket(catalog_id)
            if event.user_id:
                row["uniqueUsers"].add(event.user_id)
            if event.event_type in (CATALOG_VIEW,):
                row["views"] += 1
            elif event.event_type in (CATALOG_APPLY_CLICK, BUTTON_APPLY_CLICK):
                row["applyClicks"] += 1
            elif event.event_type in (CATALOG_TELEGRAM_CLICK, BUTTON_DETAILS_CLICK):
                row["telegramClicks"] += 1

        catalog_map = await self._catalog_map(set(item_stats.keys()))
        top_items = []
        for catalog_id, stats in item_stats.items():
            cat = catalog_map.get(catalog_id)
            if not cat:
                continue
            views = stats["views"]
            apply = stats["applyClicks"]
            tg = stats["telegramClicks"]
            unique = len(stats["uniqueUsers"])
            top_items.append(
                {
                    "catalogId": catalog_id,
                    "title": cat.title,
                    "type": cat.opportunity_type,
                    "views": views,
                    "applyClicks": apply,
                    "telegramClicks": tg,
                    "uniqueUsers": unique,
                    "ctrApply": round(apply / views * 100, 1) if views else 0,
                    "ctrTelegram": round(tg / views * 100, 1) if views else 0,
                    "totalClicks": apply + tg,
                }
            )

        top_items.sort(key=lambda x: (x["totalClicks"], x["views"]), reverse=True)
        top_items = top_items[:top_limit]

        unique_count = len(summary["uniqueUsers"])
        views = summary["views"] or 1

        recent = await self._recent_activity(since, limit=12)
        submissions = await self._user_submissions_stats(since)

        return {
            "days": days,
            "summary": {
                "views": summary["views"],
                "applyClicks": summary["applyClicks"],
                "telegramClicks": summary["telegramClicks"],
                "totalClicks": summary["applyClicks"] + summary["telegramClicks"],
                "uniqueUsers": unique_count,
                "ctrApply": round(summary["applyClicks"] / views * 100, 1) if summary["views"] else 0,
                "ctrTelegram": round(summary["telegramClicks"] / views * 100, 1) if summary["views"] else 0,
            },
            "sources": {
                "bot": {
                    "apply": summary["botApply"],
                    "telegram": summary["botTelegram"],
                },
                "miniApp": {
                    "views": summary["appViews"],
                    "apply": summary["appApply"],
                    "telegram": summary["appTelegram"],
                },
            },
            "topItems": top_items,
            "recent": recent,
            **submissions,
        }

    async def _user_submissions_stats(self, since: datetime | None) -> dict:
        stmt = (
            select(OpportunitySubmission, User.username, User.telegram_id)
            .join(User, OpportunitySubmission.user_id == User.id)
            .order_by(OpportunitySubmission.created_at.desc())
        )
        if since:
            stmt = stmt.where(OpportunitySubmission.created_at >= since)
        result = await self.session.execute(stmt)
        rows = list(result.all())

        counts = {"total": 0, "pending": 0, "approved": 0, "rejected": 0}
        by_user: dict[int, dict] = {}
        recent_list: list[dict] = []

        for sub, username, telegram_id in rows:
            counts["total"] += 1
            status = sub.status or "pending"
            if status in counts:
                counts[status] += 1

            user_ref = f"@{username}" if username else (f"id{telegram_id}" if telegram_id else "?")
            if sub.user_id not in by_user:
                by_user[sub.user_id] = {
                    "user": user_ref,
                    "telegramId": telegram_id,
                    "submissions": 0,
                    "approved": 0,
                    "pending": 0,
                }
            by_user[sub.user_id]["submissions"] += 1
            if status == "approved":
                by_user[sub.user_id]["approved"] += 1
            elif status == "pending":
                by_user[sub.user_id]["pending"] += 1

            if len(recent_list) < 15:
                recent_list.append(
                    {
                        "id": sub.id,
                        "user": user_ref,
                        "title": sub.title or sub.link or "Без названия",
                        "status": status,
                        "sourceMode": sub.source_mode,
                        "type": sub.opportunity_type,
                        "catalogId": sub.catalog_id,
                        "link": sub.link,
                        "createdAt": sub.created_at.isoformat() if sub.created_at else None,
                    }
                )

        top_contributors = sorted(
            by_user.values(),
            key=lambda x: (x["approved"], x["submissions"]),
            reverse=True,
        )[:10]

        return {
            "userSubmissions": counts,
            "recentSubmissions": recent_list,
            "topContributors": top_contributors,
        }

    async def _recent_activity(self, since: datetime | None, *, limit: int) -> list[dict]:
        types = (
            CATALOG_VIEW,
            CATALOG_APPLY_CLICK,
            CATALOG_TELEGRAM_CLICK,
            BUTTON_APPLY_CLICK,
            BUTTON_DETAILS_CLICK,
        )
        stmt = (
            select(Event, User.username, User.telegram_id, CatalogOpportunity.title)
            .outerjoin(User, Event.user_id == User.id)
            .outerjoin(
                CatalogOpportunity,
                Event.related_id == CatalogOpportunity.id,
            )
            .where(Event.event_type.in_(types))
            .order_by(Event.created_at.desc())
            .limit(limit * 2)
        )
        if since:
            stmt = stmt.where(Event.created_at >= since)
        result = await self.session.execute(stmt)
        bot_match_ids = set()
        raw_rows = []
        for event, username, telegram_id, title in result.all():
            raw_rows.append((event, username, telegram_id, title))
            if event.event_type in (BUTTON_APPLY_CLICK, BUTTON_DETAILS_CLICK) and event.related_id:
                bot_match_ids.add(event.related_id)
        match_to_catalog = await self._match_catalog_map(bot_match_ids)
        catalog_titles = await self._catalog_map(set(match_to_catalog.values()))

        rows: list[dict] = []
        for event, username, telegram_id, title in raw_rows:
            action = "view"
            if event.event_type in (CATALOG_APPLY_CLICK, BUTTON_APPLY_CLICK):
                action = "apply"
            elif event.event_type in (CATALOG_TELEGRAM_CLICK, BUTTON_DETAILS_CLICK):
                action = "telegram"
            source = "mini_app" if event.event_type.startswith("catalog_") else "bot"
            if not title and source == "bot" and event.related_id:
                cat_id = match_to_catalog.get(event.related_id)
                if cat_id and cat_id in catalog_titles:
                    title = catalog_titles[cat_id].title
            user_ref = f"@{username}" if username else (f"id{telegram_id}" if telegram_id else "?")
            rows.append(
                {
                    "action": action,
                    "source": source,
                    "title": title or "—",
                    "user": user_ref,
                    "at": event.created_at.isoformat() if event.created_at else None,
                }
            )
            if len(rows) >= limit:
                break
        return rows

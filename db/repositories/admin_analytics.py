"""Aggregations for admin tracking dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.event_types import AI_SEARCH, INTEREST_SET
from db.models import Event, MonitoredChannel, RawMessage, User, UserChannel, UserFeedback


def _utc_day_start(dt: datetime | None = None) -> datetime:
    now = dt or datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


class AdminAnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_users(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(User))
        return int(result.scalar_one())

    async def count_users_since(self, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.created_at >= since)
        )
        return int(result.scalar_one())

    async def count_active_users_since(self, since: datetime) -> int:
        event_result = await self.session.execute(
            select(Event.user_id)
            .where(Event.created_at >= since)
            .where(Event.user_id.is_not(None))
            .distinct()
        )
        updated_result = await self.session.execute(
            select(User.id).where(User.updated_at >= since)
        )
        ids = {row[0] for row in event_result.all()} | {row[0] for row in updated_result.all()}
        return len(ids)

    async def count_monitored_channels(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(MonitoredChannel).where(MonitoredChannel.is_accessible.is_(True))
        )
        return int(result.scalar_one())

    async def count_new_channels_since(self, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(MonitoredChannel).where(MonitoredChannel.created_at >= since)
        )
        return int(result.scalar_one())

    async def count_posts_since(self, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(RawMessage).where(RawMessage.fetched_at >= since)
        )
        return int(result.scalar_one())

    async def count_ai_requests_since(self, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Event)
            .where(Event.created_at >= since)
            .where(Event.event_type.in_([AI_SEARCH, INTEREST_SET]))
        )
        return int(result.scalar_one())

    async def count_ai_users_since(self, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count(func.distinct(Event.user_id)))
            .where(Event.created_at >= since)
            .where(Event.event_type.in_([AI_SEARCH, INTEREST_SET]))
            .where(Event.user_id.is_not(None))
        )
        return int(result.scalar_one())

    async def ai_requests_by_hour_today(self) -> list[int]:
        start = _utc_day_start()
        buckets = [0] * 24
        result = await self.session.execute(
            select(Event.created_at)
            .where(Event.created_at >= start)
            .where(Event.event_type.in_([AI_SEARCH, INTEREST_SET]))
        )
        for (created_at,) in result.all():
            if created_at is None:
                continue
            ts = created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            buckets[ts.hour] += 1
        return buckets

    async def recent_users(self, *, limit: int = 8) -> list[dict]:
        result = await self.session.execute(
            select(User).order_by(User.updated_at.desc(), User.created_at.desc()).limit(limit)
        )
        users = list(result.scalars().all())
        today = _utc_day_start()
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        items: list[dict] = []
        for user in users:
            ch_count = await self.session.execute(
                select(func.count()).select_from(UserChannel).where(UserChannel.user_id == user.id)
            )
            req_count = await self.session.execute(
                select(func.count())
                .select_from(Event)
                .where(Event.user_id == user.id)
                .where(Event.event_type.in_([AI_SEARCH, INTEREST_SET]))
            )
            last_event = await self.session.execute(
                select(func.max(Event.created_at)).where(Event.user_id == user.id)
            )
            last_at = last_event.scalar_one() or user.updated_at or user.created_at
            if last_at and last_at.tzinfo is None:
                last_at = last_at.replace(tzinfo=timezone.utc)
            if last_at and last_at >= today:
                status = "today"
            elif last_at and last_at >= week_ago:
                status = "recent"
            else:
                status = "inactive"
            items.append(
                {
                    "username": user.username,
                    "telegramId": user.telegram_id,
                    "channelCount": int(ch_count.scalar_one()),
                    "requestCount": int(req_count.scalar_one()),
                    "lastActiveAt": last_at.isoformat() if last_at else None,
                    "status": status,
                }
            )
        return items

    async def top_channels_by_users(self, *, limit: int = 8) -> list[dict]:
        result = await self.session.execute(
            select(MonitoredChannel)
            .where(MonitoredChannel.is_accessible.is_(True))
            .order_by(MonitoredChannel.source_count.desc(), MonitoredChannel.channel_identifier)
            .limit(limit)
        )
        channels = list(result.scalars().all())
        max_count = max((ch.source_count for ch in channels), default=1) or 1
        return [
            {
                "identifier": ch.channel_identifier,
                "title": ch.channel_title or ch.channel_identifier,
                "userCount": ch.source_count,
                "percent": round(ch.source_count / max_count * 100),
            }
            for ch in channels
            if ch.source_count > 0 or ch.is_seed
        ][:limit]

    async def scan_log(self, *, limit: int = 12) -> list[dict]:
        scan_types = (
            "channel_scan",
            "monitor_cycle_success",
            "telethon_flood_wait",
            "channel_unavailable",
        )
        result = await self.session.execute(
            select(Event)
            .where(Event.event_type.in_(scan_types))
            .order_by(Event.created_at.desc())
            .limit(limit)
        )
        items: list[dict] = []
        for event in result.scalars().all():
            meta = {}
            if event.metadata_json:
                try:
                    meta = json.loads(event.metadata_json)
                except json.JSONDecodeError:
                    meta = {}
            items.append(
                {
                    "at": event.created_at.isoformat() if event.created_at else None,
                    "type": event.event_type,
                    "meta": meta,
                }
            )
        return items

    async def feedback_list(self, *, limit: int = 10) -> tuple[list[dict], int]:
        unread = await self.session.execute(
            select(func.count()).select_from(UserFeedback).where(UserFeedback.is_read.is_(False))
        )
        unread_count = int(unread.scalar_one())
        result = await self.session.execute(
            select(UserFeedback).order_by(UserFeedback.created_at.desc()).limit(limit)
        )
        items = []
        for row in result.scalars().all():
            items.append(
                {
                    "id": row.id,
                    "username": row.username,
                    "kind": row.kind,
                    "message": row.message,
                    "source": row.source,
                    "isRead": row.is_read,
                    "createdAt": row.created_at.isoformat() if row.created_at else None,
                }
            )
        return items, unread_count

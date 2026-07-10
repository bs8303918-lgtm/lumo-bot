"""Aggregations for admin tracking dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.event_types import AI_SEARCH, CARD_SENT, INTEREST_SET
from db.models import Event, MonitoredChannel, RawMessage, SentMatch, User, UserChannel, UserFeedback
from services.ai_search_limit import ai_search_day_start_utc


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

    async def prompt_breakdown_for_users(
        self, user_ids: list[int], *, period_since: datetime
    ) -> dict[int, dict]:
        if not user_ids:
            return {}
        today_start = ai_search_day_start_utc()
        result = await self.session.execute(
            select(
                Event.user_id,
                func.count().filter(Event.event_type == AI_SEARCH).label("prompts_all"),
                func.count()
                .filter(Event.event_type == AI_SEARCH, Event.created_at >= period_since)
                .label("prompts_period"),
                func.count()
                .filter(Event.event_type == AI_SEARCH, Event.created_at >= today_start)
                .label("prompts_today"),
                func.max(Event.created_at).filter(Event.event_type == AI_SEARCH).label("last_prompt_at"),
            )
            .where(Event.user_id.in_(user_ids))
            .where(Event.event_type == AI_SEARCH)
            .group_by(Event.user_id)
        )
        out: dict[int, dict] = {}
        for uid, prompts_all, prompts_period, prompts_today, last_prompt_at in result.all():
            if last_prompt_at and last_prompt_at.tzinfo is None:
                last_prompt_at = last_prompt_at.replace(tzinfo=timezone.utc)
            out[int(uid)] = {
                "promptsAll": int(prompts_all or 0),
                "promptsPeriod": int(prompts_period or 0),
                "promptsToday": int(prompts_today or 0),
                "lastPromptAt": last_prompt_at,
            }
        return out

    async def top_active_users(self, *, since: datetime, limit: int = 15) -> list[dict]:
        """Users ranked by AI prompts in period + activity metadata."""
        activity_sq = (
            select(
                Event.user_id.label("user_id"),
                func.count().filter(Event.event_type == AI_SEARCH).label("prompts"),
                func.count().filter(Event.event_type == INTEREST_SET).label("interest_sets"),
                func.count().filter(Event.event_type == CARD_SENT).label("cards_period"),
                func.count().label("events_total"),
                func.max(Event.created_at).label("last_event_at"),
            )
            .where(Event.created_at >= since)
            .where(Event.user_id.is_not(None))
            .group_by(Event.user_id)
            .subquery()
        )
        cards_sq = (
            select(
                SentMatch.user_id.label("user_id"),
                func.count().label("cards_total"),
            )
            .group_by(SentMatch.user_id)
            .subquery()
        )
        channels_sq = (
            select(
                UserChannel.user_id.label("user_id"),
                func.count().label("channel_count"),
            )
            .group_by(UserChannel.user_id)
            .subquery()
        )

        result = await self.session.execute(
            select(
                User,
                activity_sq.c.prompts,
                activity_sq.c.interest_sets,
                activity_sq.c.cards_period,
                activity_sq.c.events_total,
                activity_sq.c.last_event_at,
                cards_sq.c.cards_total,
                channels_sq.c.channel_count,
            )
            .join(activity_sq, User.id == activity_sq.c.user_id)
            .outerjoin(cards_sq, User.id == cards_sq.c.user_id)
            .outerjoin(channels_sq, User.id == channels_sq.c.user_id)
            .order_by(
                activity_sq.c.prompts.desc(),
                activity_sq.c.events_total.desc(),
                activity_sq.c.last_event_at.desc(),
            )
            .limit(limit)
        )

        items: list[dict] = []
        for row in result.all():
            user: User = row[0]
            last_at = row[5] or user.updated_at or user.created_at
            if last_at and last_at.tzinfo is None:
                last_at = last_at.replace(tzinfo=timezone.utc)
            created = user.created_at
            if created and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            items.append(
                {
                    "userId": user.id,
                    "username": user.username,
                    "telegramId": user.telegram_id,
                    "createdAt": created,
                    "interestPreview": (user.interest_query or "")[:80],
                    "prompts": int(row[1] or 0),
                    "interestSets": int(row[2] or 0),
                    "cardsPeriod": int(row[3] or 0),
                    "eventsTotal": int(row[4] or 0),
                    "lastActiveAt": last_at,
                    "cardsTotal": int(row[6] or 0),
                    "channelCount": int(row[7] or 0),
                    "tariffPlan": user.tariff_plan,
                    "partnerSource": user.partner_source,
                }
            )

        if items:
            breakdown = await self.prompt_breakdown_for_users(
                [row["userId"] for row in items],
                period_since=since,
            )
            for row in items:
                extra = breakdown.get(row["userId"], {})
                row["promptsAll"] = extra.get("promptsAll", row["prompts"])
                row["promptsPeriod"] = extra.get("promptsPeriod", row["prompts"])
                row["promptsToday"] = extra.get("promptsToday", 0)
                row["lastPromptAt"] = extra.get("lastPromptAt")
        return items

    async def user_activity_detail(self, *, user_id: int | None = None, telegram_id: int | None = None) -> dict | None:
        stmt = select(User)
        if user_id is not None:
            stmt = stmt.where(User.id == user_id)
        elif telegram_id is not None:
            stmt = stmt.where(User.telegram_id == telegram_id)
        else:
            return None
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            return None

        now = datetime.now(timezone.utc)
        periods = {
            "today": _utc_day_start(now),
            "7d": now - timedelta(days=7),
            "30d": now - timedelta(days=30),
            "all": datetime(1970, 1, 1, tzinfo=timezone.utc),
        }
        stats: dict[str, dict[str, int]] = {}
        for label, since in periods.items():
            prompts = await self.session.execute(
                select(func.count())
                .select_from(Event)
                .where(Event.user_id == user.id)
                .where(Event.event_type == AI_SEARCH)
                .where(Event.created_at >= since)
            )
            events = await self.session.execute(
                select(func.count())
                .select_from(Event)
                .where(Event.user_id == user.id)
                .where(Event.created_at >= since)
            )
            stats[label] = {
                "prompts": int(prompts.scalar_one()),
                "events": int(events.scalar_one()),
            }

        cards = await self.session.execute(
            select(func.count()).select_from(SentMatch).where(SentMatch.user_id == user.id)
        )
        channels = await self.session.execute(
            select(func.count()).select_from(UserChannel).where(UserChannel.user_id == user.id)
        )
        last_event = await self.session.execute(
            select(func.max(Event.created_at)).where(Event.user_id == user.id)
        )
        last_prompt = await self.session.execute(
            select(func.max(Event.created_at))
            .where(Event.user_id == user.id)
            .where(Event.event_type == AI_SEARCH)
        )
        last_at = last_event.scalar_one() or user.updated_at or user.created_at
        last_prompt_at = last_prompt.scalar_one()
        if last_at and last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=timezone.utc)
        if last_prompt_at and last_prompt_at.tzinfo is None:
            last_prompt_at = last_prompt_at.replace(tzinfo=timezone.utc)
        created = user.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        return {
            "userId": user.id,
            "username": user.username,
            "telegramId": user.telegram_id,
            "createdAt": created,
            "lastActiveAt": last_at,
            "lastPromptAt": last_prompt_at,
            "interestQuery": user.interest_query,
            "channelCount": int(channels.scalar_one()),
            "cardsTotal": int(cards.scalar_one()),
            "tariffPlan": user.tariff_plan,
            "partnerSource": user.partner_source,
            "stats": stats,
        }

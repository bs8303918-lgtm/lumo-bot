"""Analyze users unreachable during maintenance broadcast."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from analytics.event_types import (
    MAINTENANCE_NOTICE_SENT,
    USER_REGISTERED,
    WELCOME_SHOWN,
    INTEREST_SET,
    CARD_SENT,
    ONBOARDING_CARDS,
    RETURNING_START,
    CAMPAIGN_SENT,
)
from config import get_settings
from db.base import async_session_factory
from db.models import Event, SentMatch, User
from services.maintenance_broadcast import get_registered_user_ids

EVENT_TYPES_OF_INTEREST = (
    USER_REGISTERED,
    WELCOME_SHOWN,
    RETURNING_START,
    INTEREST_SET,
    ONBOARDING_CARDS,
    CARD_SENT,
    CAMPAIGN_SENT,
    MAINTENANCE_NOTICE_SENT,
    "handler_error",
    "daily_digest_match",
    "daily_digest_empty",
)


async def main() -> None:
    settings = get_settings()
    days = 7
    since = datetime.now(timezone.utc) - timedelta(days=days)
    user_ids = await get_registered_user_ids(days=days)

    async with async_session_factory() as session:
        sent_result = await session.execute(
            select(Event.user_id)
            .where(Event.event_type == MAINTENANCE_NOTICE_SENT)
            .where(Event.metadata_json.contains("maintenance_2026-06-24"))
        )
        sent_ids = {row[0] for row in sent_result.all()}
        unreachable_ids = [uid for uid in user_ids if uid not in sent_ids]

        print(f"Registered ({days}d): {len(user_ids)}")
        print(f"Maintenance sent: {len(sent_ids)}")
        print(f"Unreachable (no delivery event): {len(unreachable_ids)}")
        print(f"WebApp URL now: {settings.resolved_webapp_url or '(empty)'}")
        print()

        for user_id in unreachable_ids:
            user = await session.get(User, user_id)
            if not user:
                continue
            ref = f"@{user.username}" if user.username else f"tg:{user.telegram_id}"
            print("=" * 60)
            print(f"User #{user_id} {ref} telegram_id={user.telegram_id}")
            print(f"  created_at: {user.created_at}")
            print(f"  interest: {(user.interest_query or '')[:80] or '(none)'}")
            print(f"  notifications_enabled: {user.notifications_enabled}")

            events = await session.execute(
                select(Event)
                .where(Event.user_id == user_id)
                .order_by(Event.created_at.asc())
            )
            rows = list(events.scalars().all())
            print(f"  events ({len(rows)}):")
            for ev in rows:
                meta = ""
                if ev.metadata_json:
                    try:
                        data = json.loads(ev.metadata_json)
                        if isinstance(data, dict) and data:
                            meta = " " + json.dumps(data, ensure_ascii=False)[:120]
                    except json.JSONDecodeError:
                        pass
                print(f"    {ev.created_at}  {ev.event_type}{meta}")

            matches = await session.execute(
                select(SentMatch)
                .where(SentMatch.user_id == user_id)
                .order_by(SentMatch.sent_at.desc())
                .limit(3)
            )
            sent = list(matches.scalars().all())
            if sent:
                print(f"  last cards sent:")
                for m in sent:
                    print(f"    {m.sent_at} match_id={m.id}")

            # gap between registration and last bot-side event
            reg = next((e for e in rows if e.event_type == USER_REGISTERED), None)
            last = rows[-1] if rows else None
            if reg and last:
                gap = last.created_at - reg.created_at
                print(f"  span reg -> last event: {gap}")

        # aggregate: when did unreachable users register
        print("\n=== UNREACHABLE REGISTRATION TIMES ===")
        for user_id in unreachable_ids:
            user = await session.get(User, user_id)
            if user:
                print(f"  {user.created_at}  id={user_id}  @{user.username or '?'}")

        # compare: did they get welcome?
        print("\n=== WELCOME vs NO-WELCOME among unreachable ===")
        for user_id in unreachable_ids:
            ev = await session.execute(
                select(Event.created_at)
                .where(Event.user_id == user_id)
                .where(Event.event_type == WELCOME_SHOWN)
                .limit(1)
            )
            w = ev.scalar_one_or_none()
            user = await session.get(User, user_id)
            ref = user.username if user else "?"
            print(f"  id={user_id} @{ref} welcome={w or 'NO'}")


if __name__ == "__main__":
    asyncio.run(main())

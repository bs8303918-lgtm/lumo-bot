"""Rank most active users: mini app, catalog, prompts, Telegram clicks."""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from analytics.event_types import (
    AI_SEARCH,
    BROWSE_CATEGORY_CLICK,
    BUTTON_APPLY_CLICK,
    BUTTON_DETAILS_CLICK,
    CARD_SENT,
    CATALOG_APPLY_CLICK,
    CATALOG_TELEGRAM_CLICK,
    CATALOG_VIEW,
    INTEREST_SET,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config import BASE_DIR, get_settings
from db.models import Event, User

_KZ = timezone(timedelta(hours=5))

SIGNAL_EVENTS = frozenset(
    {
        AI_SEARCH,
        INTEREST_SET,
        CATALOG_VIEW,
        CATALOG_APPLY_CLICK,
        CATALOG_TELEGRAM_CLICK,
        BUTTON_DETAILS_CLICK,
        BUTTON_APPLY_CLICK,
        BROWSE_CATEGORY_CLICK,
        CARD_SENT,
    }
)

WEIGHTS = {
    AI_SEARCH: 4,
    CATALOG_VIEW: 3,
    CATALOG_TELEGRAM_CLICK: 5,
    CATALOG_APPLY_CLICK: 4,
    BUTTON_DETAILS_CLICK: 5,
    BUTTON_APPLY_CLICK: 4,
    BROWSE_CATEGORY_CLICK: 2,
    CARD_SENT: 1,
    INTEREST_SET: 1,
}


def _sqlite_url() -> str:
    return f"sqlite+aiosqlite:///{(BASE_DIR / 'lumo.db').as_posix()}"


def _local_day(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_KZ).date().isoformat()


def _ago(dt: datetime | None, now: datetime) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    mins = int((now - dt).total_seconds() / 60)
    if mins < 60:
        return f"{mins} мин"
    hours = mins // 60
    if hours < 48:
        return f"{hours} ч"
    return f"{hours // 24} дн"


async def _load(url: str) -> list[tuple]:
    engine = create_async_engine(url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            users = {
                int(r[0]): {"username": r[1], "interest": (r[2] or "")[:60]}
                for r in (
                    await session.execute(select(User.telegram_id, User.username, User.interest_query))
                ).all()
            }
            rows = (
                await session.execute(
                    select(User.telegram_id, Event.event_type, Event.created_at)
                    .join(Event, Event.user_id == User.id)
                    .where(Event.event_type.in_(SIGNAL_EVENTS))
                )
            ).all()
        return [(users, rows)]
    finally:
        await engine.dispose()


def _merge_and_rank(
    blocks: list,
    *,
    now: datetime,
    top_n: int = 25,
    recent_days: int = 30,
) -> list[dict]:
    merged: dict[int, dict] = {}
    recent_cutoff = now - timedelta(days=recent_days)

    for users_map, rows in blocks:
        for tid, meta in users_map.items():
            merged.setdefault(
                tid,
                {
                    "username": meta["username"],
                    "interest": meta["interest"],
                    "counts": defaultdict(int),
                    "activeDays": set(),
                    "lastAt": None,
                },
            )
            if meta["username"] and not merged[tid]["username"]:
                merged[tid]["username"] = meta["username"]
            if meta["interest"] and not merged[tid]["interest"]:
                merged[tid]["interest"] = meta["interest"]

        for tg_id, event_type, created_at in rows:
            tid = int(tg_id)
            bucket = merged.setdefault(
                tid,
                {
                    "username": users_map.get(tid, {}).get("username"),
                    "interest": users_map.get(tid, {}).get("interest", ""),
                    "counts": defaultdict(int),
                    "activeDays": set(),
                    "lastAt": None,
                },
            )
            bucket["counts"][event_type] += 1
            if created_at:
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                bucket["activeDays"].add(_local_day(created_at))
                if bucket["lastAt"] is None or created_at > bucket["lastAt"]:
                    bucket["lastAt"] = created_at

    ranked: list[dict] = []
    for tid, data in merged.items():
        counts = data["counts"]
        prompts = counts.get(AI_SEARCH, 0)
        catalog_views = counts.get(CATALOG_VIEW, 0)
        tg_clicks = counts.get(CATALOG_TELEGRAM_CLICK, 0) + counts.get(BUTTON_DETAILS_CLICK, 0)
        apply_clicks = counts.get(CATALOG_APPLY_CLICK, 0) + counts.get(BUTTON_APPLY_CLICK, 0)
        browse = counts.get(BROWSE_CATEGORY_CLICK, 0)
        cards = counts.get(CARD_SENT, 0)
        interest = counts.get(INTEREST_SET, 0)

        score = sum(counts.get(ev, 0) * WEIGHTS.get(ev, 1) for ev in counts)
        score += len(data["activeDays"]) * 2  # multi-day bonus

        signal_types = sum(
            1
            for key in (
                prompts,
                catalog_views,
                tg_clicks,
                apply_clicks,
                browse,
            )
            if key > 0
        )

        last_at = data["lastAt"]
        is_recent = bool(last_at and last_at >= recent_cutoff)

        # Meaningful: at least 2 weighted actions OR multi-signal OR 2+ prompts
        actions = prompts + catalog_views + tg_clicks + apply_clicks + browse
        if actions < 2 and signal_types < 2 and prompts < 2:
            continue

        ranked.append(
            {
                "telegramId": tid,
                "username": data["username"],
                "score": score,
                "prompts": prompts,
                "catalogViews": catalog_views,
                "telegramClicks": tg_clicks,
                "applyClicks": apply_clicks,
                "browseClicks": browse,
                "cardsSent": cards,
                "interestSets": interest,
                "activeDays": len(data["activeDays"]),
                "lastActiveAgo": _ago(last_at, now),
                "lastActiveAt": last_at.isoformat() if last_at else None,
                "isRecent": is_recent,
                "interest": data["interest"],
                "contact": f"@{data['username'].lstrip('@')}" if data["username"] else f"id:{tid}",
                "tmeLink": f"https://t.me/{data['username'].lstrip('@')}" if data["username"] else None,
            }
        )

    ranked.sort(
        key=lambda r: (
            r["isRecent"],
            r["score"],
            r["prompts"],
            r["telegramClicks"],
            r["catalogViews"],
        ),
        reverse=True,
    )
    return ranked[:top_n]


async def main() -> None:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    blocks = []
    for url in (_sqlite_url(), settings.database_url):
        try:
            blocks.extend(await _load(url))
        except Exception as exc:
            print(json.dumps({"error": str(exc)[:200]}), file=sys.stderr)

    top = _merge_and_rank(blocks, now=now, top_n=30)

    print(json.dumps({"generatedAt": now.isoformat(), "topActiveUsers": top}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

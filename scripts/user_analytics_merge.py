"""Merge user counts from local SQLite and Supabase; /start vs returning analytics."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from analytics.event_types import RETURNING_START, USER_REGISTERED
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import BASE_DIR, get_settings
from db.base import configure_supabase_pooler
from db.models import Event, User


def _sqlite_url() -> str:
    path = BASE_DIR / "lumo.db"
    return f"sqlite+aiosqlite:///{path.as_posix()}"


async def _fetch_stats(session: AsyncSession, label: str) -> dict:
    users_total = int((await session.execute(select(func.count()).select_from(User))).scalar_one())
    users_with_username = int(
        (await session.execute(select(func.count()).select_from(User).where(User.username.is_not(None)))).scalar_one()
    )

    reg_users = int(
        (
            await session.execute(
                select(func.count(func.distinct(Event.user_id)))
                .where(Event.event_type == USER_REGISTERED)
                .where(Event.user_id.is_not(None))
            )
        ).scalar_one()
    )
    returning_users = int(
        (
            await session.execute(
                select(func.count(func.distinct(Event.user_id)))
                .where(Event.event_type == RETURNING_START)
                .where(Event.user_id.is_not(None))
            )
        ).scalar_one()
    )
    reg_events = int(
        (await session.execute(select(func.count()).select_from(Event).where(Event.event_type == USER_REGISTERED))).scalar_one()
    )
    returning_events = int(
        (
            await session.execute(
                select(func.count()).select_from(Event).where(Event.event_type == RETURNING_START)
            )
        ).scalar_one()
    )

    tg_rows = await session.execute(select(User.telegram_id, User.username, User.created_at))
    telegram_ids: dict[int, dict] = {}
    for tg_id, username, created_at in tg_rows.all():
        telegram_ids[int(tg_id)] = {
            "username": username,
            "createdAt": created_at.isoformat() if created_at else None,
        }

    return {
        "label": label,
        "usersTotal": users_total,
        "usersWithUsername": users_with_username,
        "firstStartUsers": reg_users,
        "returningStartUsers": returning_users,
        "firstStartEvents": reg_events,
        "returningStartEvents": returning_events,
        "telegramIds": telegram_ids,
    }


async def _try_fetch(url: str, label: str) -> dict | None:
    engine = create_async_engine(url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            if url.startswith("sqlite"):
                await session.execute(text("SELECT 1"))
            else:
                configure_supabase_pooler()
                await session.execute(text("SELECT 1"))
            return await _fetch_stats(session, label)
    except Exception as exc:
        return {"label": label, "error": str(exc)[:200]}
    finally:
        await engine.dispose()


def _merge(sets: list[dict]) -> dict:
    all_ids: dict[int, dict] = {}
    for block in sets:
        if block.get("error"):
            continue
        for tg_id, meta in block.get("telegramIds", {}).items():
            if tg_id not in all_ids:
                all_ids[tg_id] = {**meta, "sources": [block["label"]]}
            else:
                all_ids[tg_id]["sources"].append(block["label"])

    only_sqlite = [k for k, v in all_ids.items() if v["sources"] == ["local SQLite (lumo.db)"]]
    only_supabase = [k for k, v in all_ids.items() if v["sources"] == ["Supabase (production)"]]
    both = [k for k, v in all_ids.items() if len(v["sources"]) == 2]

    return {
        "uniqueUsersTotal": len(all_ids),
        "inBothDatabases": len(both),
        "onlyLocalSqlite": len(only_sqlite),
        "onlySupabase": len(only_supabase),
    }


async def main() -> None:
    settings = get_settings()
    supabase_url = settings.database_url
    is_sqlite_prod = supabase_url.startswith("sqlite")

    results: list[dict] = []
    local = await _try_fetch(_sqlite_url(), "local SQLite (lumo.db)")
    results.append(local)

    if is_sqlite_prod:
        prod = {**local, "label": "Supabase (production)", "note": "DATABASE_URL points to sqlite — same as local"}
    else:
        prod = await _try_fetch(supabase_url, "Supabase (production)")
    results.append(prod)

    merge = _merge(results)

    first_start_ids: set[int] = set()
    returning_start_ids: set[int] = set()
    for block in results:
        if block.get("error"):
            continue
        label = block["label"]
        url = _sqlite_url() if label.startswith("local") else supabase_url
        engine = create_async_engine(url, echo=False)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                rows = await session.execute(
                    select(User.telegram_id, Event.event_type)
                    .join(Event, Event.user_id == User.id)
                    .where(Event.event_type.in_([USER_REGISTERED, RETURNING_START]))
                )
                for tg_id, event_type in rows.all():
                    tid = int(tg_id)
                    if event_type == USER_REGISTERED:
                        first_start_ids.add(tid)
                    else:
                        returning_start_ids.add(tid)
        finally:
            await engine.dispose()

    start_analytics = {
        "uniqueFirstStartUsers": len(first_start_ids),
        "uniqueReturningStartUsers": len(returning_start_ids),
        "onlyFirstStartNeverReturning": len(first_start_ids - returning_start_ids),
        "firstAndReturningBoth": len(first_start_ids & returning_start_ids),
        "returningWithoutRegisteredEvent": len(returning_start_ids - first_start_ids),
    }

    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "databases": [
            {k: v for k, v in r.items() if k != "telegramIds"}
            for r in results
        ],
        "merged": merge,
        "startAnalytics": start_analytics,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

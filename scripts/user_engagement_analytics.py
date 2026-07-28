"""Engagement analytics: interest/prompt users and next-day prompt return."""

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

from analytics.event_types import AI_SEARCH, INTEREST_SET
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config import BASE_DIR, get_settings
from db.models import Event, User

_KZ = timezone(timedelta(hours=5))


def _sqlite_url() -> str:
    return f"sqlite+aiosqlite:///{(BASE_DIR / 'lumo.db').as_posix()}"


def _local_day(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_KZ).date().isoformat()


async def _load_engagement(url: str, label: str) -> dict:
    engine = create_async_engine(url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            rows = await session.execute(
                select(User.telegram_id, Event.event_type, Event.created_at)
                .join(Event, Event.user_id == User.id)
                .where(Event.event_type.in_([AI_SEARCH, INTEREST_SET]))
                .order_by(User.telegram_id, Event.created_at)
            )
            per_user: dict[int, dict] = {}
            for tg_id, event_type, created_at in rows.all():
                tid = int(tg_id)
                bucket = per_user.setdefault(
                    tid,
                    {"promptDays": set(), "promptCount": 0, "hasInterest": False},
                )
                if event_type == INTEREST_SET:
                    bucket["hasInterest"] = True
                else:
                    bucket["promptCount"] += 1
                    if created_at:
                        bucket["promptDays"].add(_local_day(created_at))
            return {"label": label, "users": per_user}
    except Exception as exc:
        return {"label": label, "error": str(exc)[:300], "users": {}}
    finally:
        await engine.dispose()


def _classify_user(data: dict) -> str:
    prompt_days = sorted(data["promptDays"])
    has_interest = data["hasInterest"]
    prompt_count = data["promptCount"]

    if prompt_count == 0 and has_interest:
        return "interest_only"
    if prompt_count == 0:
        return "none"
    if len(prompt_days) == 1:
        return "prompt_single_day"
    # 2+ days with prompts
    for i in range(1, len(prompt_days)):
        d0 = datetime.fromisoformat(prompt_days[i - 1]).date()
        d1 = datetime.fromisoformat(prompt_days[i]).date()
        if (d1 - d0).days >= 1:
            return "prompt_returned_another_day"
    return "prompt_multi_same_day"


def _merge_users(blocks: list[dict]) -> dict[int, dict]:
    merged: dict[int, dict] = {}
    for block in blocks:
        for tid, data in block.get("users", {}).items():
            if tid not in merged:
                merged[tid] = {
                    "promptDays": set(data["promptDays"]),
                    "promptCount": data["promptCount"],
                    "hasInterest": data["hasInterest"],
                    "sources": [block["label"]],
                }
            else:
                merged[tid]["promptDays"] |= data["promptDays"]
                merged[tid]["promptCount"] += data["promptCount"]
                merged[tid]["hasInterest"] = merged[tid]["hasInterest"] or data["hasInterest"]
                merged[tid]["sources"].append(block["label"])
    return merged


def _summarize(users: dict[int, dict], *, label: str) -> dict:
    classes = defaultdict(int)
    engaged = 0
    for data in users.values():
        if data["promptCount"] > 0 or data["hasInterest"]:
            engaged += 1
        classes[_classify_user(data)] += 1

    prompt_users = sum(1 for d in users.values() if d["promptCount"] > 0)
    interest_users = sum(1 for d in users.values() if d["hasInterest"])
    interest_and_prompt = sum(
        1 for d in users.values() if d["hasInterest"] and d["promptCount"] > 0
    )

    return {
        "label": label,
        "usersInTable": len(users),
        "engagedInterestOrPrompt": engaged,
        "withInterest": interest_users,
        "withPrompt": prompt_users,
        "withInterestAndPrompt": interest_and_prompt,
        "interestOnlyNoPrompt": classes["interest_only"],
        "promptSingleDayOnly": classes["prompt_single_day"],
        "promptReturnedAnotherDay": classes["prompt_returned_another_day"],
        "promptMultiSameDayOnly": classes["prompt_multi_same_day"],
        "totalPromptEvents": sum(d["promptCount"] for d in users.values()),
    }


async def main() -> None:
    settings = get_settings()
    blocks = [
        await _load_engagement(_sqlite_url(), "local SQLite"),
        await _load_engagement(settings.database_url, "Supabase"),
    ]

    merged_users = _merge_users(blocks)

    # All registered users count from both DBs
    all_telegram_ids: set[int] = set()
    for url, label in [(_sqlite_url(), "local"), (settings.database_url, "supabase")]:
        engine = create_async_engine(url, echo=False)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                rows = await session.execute(select(User.telegram_id))
                all_telegram_ids |= {int(r[0]) for r in rows.all()}
        except Exception:
            pass
        finally:
            await engine.dispose()

    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "timezone": "Asia/Almaty (UTC+5) for day boundaries",
        "definitions": {
            "engaged": "хотя бы interest_set или ai_search",
            "promptReturnedAnotherDay": "2+ промпта в разные календарные дни (минимум через 1 день)",
            "promptSingleDayOnly": "промпты были, но все в один день",
            "interestOnly": "сохранил интерес, промптов нет",
        },
        "totalUniqueUsersAllDatabases": len(all_telegram_ids),
        "perDatabase": [_summarize(b.get("users", {}), label=b["label"]) for b in blocks if not b.get("error")],
        "mergedUnique": _summarize(merged_users, label="merged (no duplicate telegram_id)"),
        "databaseErrors": [b for b in blocks if b.get("error")],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

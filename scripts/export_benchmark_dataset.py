"""Export raw Telegram posts from DB (raw_messages — без обработки LLM)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from benchmark.schema import write_jsonl
from config import get_settings
from db.base import async_session_factory
from db.models import MonitoredChannel, RawMessage


async def export_raw_posts(
    *,
    limit: int,
    output: Path,
    min_length: int,
) -> int:
    settings = get_settings()

    async with async_session_factory() as session:
        stmt = (
            select(
                RawMessage.id,
                RawMessage.text,
                RawMessage.message_link,
                RawMessage.posted_at,
                MonitoredChannel.channel_title,
                MonitoredChannel.channel_identifier,
            )
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(RawMessage.text.is_not(None))
            .order_by(RawMessage.posted_at.desc().nullslast(), RawMessage.id.desc())
            .limit(limit * 2)
        )
        rows = (await session.execute(stmt)).all()

    export_rows: list[dict] = []
    for row in rows:
        text = (row.text or "").strip()
        if len(text) < min_length:
            continue
        export_rows.append(
            {
                "id": f"raw_{row.id}",
                "raw_message_id": row.id,
                "message_link": row.message_link,
                "source_channel": row.channel_title or row.channel_identifier,
                "posted_at": row.posted_at.isoformat() if row.posted_at else None,
                "message_text": text,
                "golden": None,
                "notes": "Необработанный пост из raw_messages. Опционально: заполните golden для сравнения с эталоном.",
            }
        )
        if len(export_rows) >= limit:
            break

    write_jsonl(output, export_rows)
    print(f"Exported {len(export_rows)} raw posts -> {output}")
    print("Source: raw_messages (текст как в Telegram, до LLM-классификации)")
    print(f"DB: {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}")
    return len(export_rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export unprocessed Telegram posts from raw_messages for LLM benchmark"
    )
    parser.add_argument("--limit", type=int, default=200, help="Max posts (default: 200)")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "benchmark" / "posts.jsonl",
        help="Output JSONL path",
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=40,
        help="Skip very short messages (default: 40 chars)",
    )
    args = parser.parse_args()
    asyncio.run(
        export_raw_posts(
            limit=args.limit,
            output=args.output,
            min_length=args.min_length,
        )
    )


if __name__ == "__main__":
    main()

"""Push active Lumo catalog to Startify webhook (initial seed / backfill).

Usage:
  python scripts/push_catalog_to_startify.py
  python scripts/push_catalog_to_startify.py --limit 20
  python scripts/push_catalog_to_startify.py --updated   # use opportunity.updated
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from db.base import configure_supabase_pooler  # noqa: E402
from services.startify_catalog_push import (  # noqa: E402
    EVENT_CREATED,
    EVENT_UPDATED,
    is_push_configured,
    push_all_active_catalog,
)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed/backfill Startify catalog")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--updated",
        action="store_true",
        help="Send opportunity.updated instead of opportunity.created",
    )
    args = parser.parse_args()

    configure_supabase_pooler()
    if not is_push_configured():
        print(
            "Set STARTIFY_CATALOG_WEBHOOK_URL and PARTNER_API_KEY in env.\n"
            "Prod: https://api.aistartify.com/api/webhooks/lumo/catalog\n"
            "Dev:  https://api-dev.aistartify.com/api/webhooks/lumo/catalog"
        )
        raise SystemExit(1)

    event = EVENT_UPDATED if args.updated else EVENT_CREATED
    stats = await push_all_active_catalog(limit=args.limit, event=event)
    print(
        f"Done ({event}): total={stats['total']} pushed={stats['pushed']} failed={stats['failed']}"
    )
    if stats["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

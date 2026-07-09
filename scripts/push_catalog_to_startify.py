"""Push active Lumo catalog to Startify webhook (initial backfill)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from db.base import configure_supabase_pooler  # noqa: E402
from services.startify_catalog_push import is_push_configured, push_all_active_catalog  # noqa: E402


async def main() -> None:
    configure_supabase_pooler()
    if not is_push_configured():
        print(
            "Set STARTIFY_CATALOG_WEBHOOK_URL and PARTNER_API_KEY in env "
            "(see docs/STARTIFY_CATALOG_WEBHOOK.md)"
        )
        raise SystemExit(1)
    stats = await push_all_active_catalog()
    print(
        f"Done: total={stats['total']} pushed={stats['pushed']} failed={stats['failed']}"
    )
    if stats["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

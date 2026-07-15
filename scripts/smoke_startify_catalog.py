"""Smoke-test AI Startify catalog webhook (create + deactivate).

Usage:
  python scripts/smoke_startify_catalog.py
  python scripts/smoke_startify_catalog.py prod

Requires PARTNER_API_KEY in env (.env or Railway).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import get_settings  # noqa: E402

DEV_URL = "https://api-dev.aistartify.com/api/webhooks/lumo/catalog"
PROD_URL = "https://api.aistartify.com/api/webhooks/lumo/catalog"
SMOKE_ID = 999999001


async def _post(url: str, key: str, payload: dict) -> tuple[int, str]:
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(url, json=payload, headers=headers)
    return res.status_code, res.text


async def main() -> None:
    settings = get_settings()
    key = settings.partner_api_key.strip()
    if not key:
        print("PARTNER_API_KEY is empty — set it in .env / Railway")
        raise SystemExit(1)

    use_prod = "prod" in {a.lower() for a in sys.argv[1:]}
    url = (
        settings.startify_catalog_webhook_url.strip()
        or (PROD_URL if use_prod else DEV_URL)
    )
    if use_prod and "api-dev" in url:
        url = PROD_URL

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    create_payload = {
        "event": "opportunity.created",
        "sentAt": now,
        "source": "lumo-catalog",
        "opportunity": {
            "id": SMOKE_ID,
            "type": "grant",
            "title": "Lumo smoke test grant",
            "description": "Temporary smoke test from Lumo — safe to deactivate",
            "deadline": "31 декабря 2026",
            "applicationUrl": "https://example.com/lumo-smoke",
            "emoji": "🏆",
            "tags": ["test", "lumo"],
            "isPremium": False,
            "isActive": True,
        },
    }
    deactivate_payload = {
        "event": "opportunity.deactivated",
        "sentAt": now,
        "source": "lumo-catalog",
        "opportunity": {"id": SMOKE_ID},
    }

    print(f"URL: {url}")
    status, body = await _post(url, key, create_payload)
    print(f"CREATE HTTP {status} {body[:200]}")
    if status >= 300:
        raise SystemExit(1)

    status, body = await _post(url, key, deactivate_payload)
    print(f"DEACTIVATE HTTP {status} {body[:200]}")
    if status >= 300:
        raise SystemExit(1)
    print("OK - Startify catalog webhook smoke passed")


if __name__ == "__main__":
    asyncio.run(main())

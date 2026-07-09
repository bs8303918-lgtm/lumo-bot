"""Push catalog opportunities from Lumo monitoring to Startify webhook."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from config import get_settings
from db.base import async_session_factory
from services.opportunity_catalog import catalog_repo
from services.webapp_catalog import dedupe_opportunities, serialize_opportunity, sort_opportunities_by_deadline

logger = logging.getLogger(__name__)

EVENT_CREATED = "opportunity.created"
EVENT_UPDATED = "opportunity.updated"
EVENT_DEACTIVATED = "opportunity.deactivated"


def is_push_configured() -> bool:
    settings = get_settings()
    if not settings.startify_catalog_push_enabled:
        return False
    return bool(settings.startify_catalog_webhook_url.strip() and settings.partner_api_key.strip())


def build_webhook_payload(event: str, opportunity: dict) -> dict:
    return {
        "event": event,
        "sentAt": datetime.now(timezone.utc).isoformat(),
        "source": "lumo",
        "opportunity": opportunity,
    }


async def push_catalog_opportunity_by_id(catalog_id: int, *, event: str = EVENT_CREATED) -> bool:
    """Load catalog entry and POST to Startify. Returns True on HTTP 2xx."""
    if not is_push_configured():
        return False

    async with async_session_factory() as session:
        entry = await catalog_repo(session).get_by_id(catalog_id)
        if not entry:
            logger.warning("Startify push: catalog %s not found", catalog_id)
            return False
        opportunity = serialize_opportunity(entry)
        if event == EVENT_DEACTIVATED:
            opportunity = {**opportunity, "isActive": False}
        elif event in (EVENT_CREATED, EVENT_UPDATED):
            opportunity = {**opportunity, "isActive": bool(entry.is_active)}

    return await _post_webhook(build_webhook_payload(event, opportunity))


async def _post_webhook(payload: dict) -> bool:
    settings = get_settings()
    url = settings.startify_catalog_webhook_url.strip()
    key = settings.partner_api_key.strip()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    opp_id = payload.get("opportunity", {}).get("id")
    event = payload.get("event")

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, json=payload, headers=headers)
            if response.status_code < 300:
                logger.info("Startify catalog push ok: event=%s id=%s", event, opp_id)
                return True
            logger.warning(
                "Startify catalog push HTTP %s for id=%s: %s",
                response.status_code,
                opp_id,
                response.text[:300],
            )
        except httpx.HTTPError as exc:
            logger.warning("Startify catalog push error id=%s attempt=%s: %s", opp_id, attempt + 1, exc)
        if attempt < 2:
            await asyncio.sleep(2**attempt)
    return False


def schedule_catalog_push(catalog_ids: list[int], *, event: str = EVENT_CREATED) -> None:
    """Fire-and-forget push after new catalog entries appear."""
    if not catalog_ids or not is_push_configured():
        return

    async def _run() -> None:
        for catalog_id in catalog_ids:
            try:
                await push_catalog_opportunity_by_id(catalog_id, event=event)
            except Exception as exc:
                logger.warning("Startify catalog push failed id=%s: %s", catalog_id, exc)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_run())


async def push_all_active_catalog(*, limit: int | None = None) -> dict[str, int]:
    """Backfill active catalog entries to Startify (manual or script)."""
    if not is_push_configured():
        return {"pushed": 0, "failed": 0, "skipped": 0, "total": 0}

    async with async_session_factory() as session:
        repo = catalog_repo(session)
        entries = sort_opportunities_by_deadline(dedupe_opportunities(await repo.list_all_public_active()))
    if limit is not None:
        entries = entries[:limit]

    pushed = failed = 0
    for entry in entries:
        ok = await push_catalog_opportunity_by_id(entry.id, event=EVENT_UPDATED)
        if ok:
            pushed += 1
        else:
            failed += 1
    return {"pushed": pushed, "failed": failed, "skipped": 0, "total": len(entries)}

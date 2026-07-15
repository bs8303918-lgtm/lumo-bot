"""Push catalog opportunities from Lumo monitoring to AI Startify webhook.

Contract: docs from Startify Rev 1.0 (2026-07-13)
  POST {STARTIFY_CATALOG_WEBHOOK_URL}
  Authorization: Bearer {PARTNER_API_KEY}
  source: lumo-catalog
  type: grant | internship | event
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from config import get_settings
from db.base import async_session_factory
from db.models import CatalogOpportunity
from db.repositories.opportunity_catalog import OpportunityCatalogRepository
from services.webapp_catalog import (
    clean_source_name,
    dedupe_opportunities,
    entry_all_tags,
    normalize_application_url,
    normalize_message_link,
    pick_telegram_post_link,
    sort_opportunities_by_deadline,
)

logger = logging.getLogger(__name__)

EVENT_CREATED = "opportunity.created"
EVENT_UPDATED = "opportunity.updated"
EVENT_DEACTIVATED = "opportunity.deactivated"

SOURCE = "lumo-catalog"

# Lumo Russian types → Startify tab types
_TYPE_MAP = {
    "грант": "grant",
    "стипендия": "grant",
    "стажировка": "internship",
    "хакатон": "event",
    "конкурс": "event",
    "олимпиада": "event",
    "эссе": "event",
    "кейс": "event",
    "летняя_школа": "event",
    "курс": "event",
    "мероприятие": "event",
    "зритель": "event",
    "другое": "event",
}

_RETRY_DELAYS = (0.5, 1.0, 2.0)


def _catalog_repo(session) -> OpportunityCatalogRepository:
    settings = get_settings()
    return OpportunityCatalogRepository(
        session,
        no_deadline_max_age_days=settings.catalog_no_deadline_max_age_days,
    )


def is_push_configured() -> bool:
    settings = get_settings()
    if not settings.startify_catalog_push_enabled:
        return False
    return bool(settings.startify_catalog_webhook_url.strip() and settings.partner_api_key.strip())


def map_startify_type(opportunity_type: str | None) -> str:
    key = (opportunity_type or "").strip().lower()
    return _TYPE_MAP.get(key, "event")


def serialize_for_startify(entry: CatalogOpportunity, *, is_active: bool | None = None) -> dict:
    """Payload shape required by AI Startify catalog webhook."""
    app_url = normalize_application_url(entry.application_url)
    msg_link = pick_telegram_post_link(entry.message_link, entry.application_url)
    if not msg_link:
        msg_link = normalize_message_link(entry.message_link)

    title = (entry.title or "").strip() or "Без названия"
    if len(title) > 80:
        title = title[:77].rstrip() + "…"

    description = (entry.description or "").strip() or title
    deadline = (entry.deadline or "").strip() or "не указан"

    tags = [str(t) for t in entry_all_tags(entry) if t]
    emoji = None
    label = None
    from services.interest_matcher import CATEGORY_DISPLAY

    if entry.opportunity_type in CATEGORY_DISPLAY:
        emoji, label = CATEGORY_DISPLAY[entry.opportunity_type]

    active = entry.is_active if is_active is None else is_active

    payload = {
        "id": int(entry.id),
        "type": map_startify_type(entry.opportunity_type),
        "title": title,
        "description": description,
        "deadline": deadline,
        "requirements": (entry.requirements or None),
        "applicationUrl": app_url or None,
        "messageLink": msg_link or None,
        "sourceChannelName": clean_source_name(entry.source_channel_name) or None,
        "emoji": emoji,
        "label": label,
        "tags": tags,
        "isPremium": False,
        "isActive": bool(active),
    }
    if not payload["applicationUrl"] and not payload["messageLink"]:
        logger.warning(
            "Startify push id=%s has neither applicationUrl nor messageLink",
            entry.id,
        )
    return payload


def build_webhook_payload(event: str, opportunity: dict) -> dict:
    return {
        "event": event,
        "sentAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": SOURCE,
        "opportunity": opportunity,
    }


async def push_catalog_opportunity_by_id(catalog_id: int, *, event: str = EVENT_CREATED) -> bool:
    """Load catalog entry and POST to Startify. Returns True on HTTP 2xx."""
    if not is_push_configured():
        return False

    async with async_session_factory() as session:
        entry = await _catalog_repo(session).get_by_id(catalog_id)
        if not entry:
            logger.warning("Startify push: catalog %s not found", catalog_id)
            return False

        if event == EVENT_DEACTIVATED:
            opportunity = {"id": int(entry.id), "isActive": False}
        else:
            opportunity = serialize_for_startify(entry, is_active=bool(entry.is_active))

    return await _post_webhook(build_webhook_payload(event, opportunity))


async def push_deactivated_ids(catalog_ids: list[int]) -> dict[str, int]:
    stats = {"pushed": 0, "failed": 0, "total": len(catalog_ids)}
    for catalog_id in catalog_ids:
        ok = await push_catalog_opportunity_by_id(catalog_id, event=EVENT_DEACTIVATED)
        if ok:
            stats["pushed"] += 1
        else:
            stats["failed"] += 1
    return stats


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

    for attempt, delay in enumerate(_RETRY_DELAYS):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, json=payload, headers=headers)
            if response.status_code < 300:
                logger.info("Startify catalog push ok: event=%s id=%s", event, opp_id)
                return True
            # 4xx — do not retry (validation / auth)
            if 400 <= response.status_code < 500:
                logger.warning(
                    "Startify catalog push HTTP %s (no retry) id=%s: %s",
                    response.status_code,
                    opp_id,
                    response.text[:300],
                )
                return False
            logger.warning(
                "Startify catalog push HTTP %s for id=%s: %s",
                response.status_code,
                opp_id,
                response.text[:300],
            )
        except httpx.HTTPError as exc:
            logger.warning("Startify catalog push error id=%s attempt=%s: %s", opp_id, attempt + 1, exc)
        if attempt < len(_RETRY_DELAYS) - 1:
            await asyncio.sleep(delay)
    return False


def schedule_catalog_push(catalog_ids: list[int], *, event: str = EVENT_CREATED) -> None:
    """Fire-and-forget push after catalog changes."""
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


def schedule_catalog_deactivate(catalog_ids: list[int]) -> None:
    schedule_catalog_push(catalog_ids, event=EVENT_DEACTIVATED)


async def push_all_active_catalog(
    *,
    limit: int | None = None,
    event: str = EVENT_CREATED,
) -> dict[str, int]:
    """Backfill / seed active catalog to Startify."""
    if not is_push_configured():
        return {"pushed": 0, "failed": 0, "skipped": 0, "total": 0}

    async with async_session_factory() as session:
        repo = _catalog_repo(session)
        entries = sort_opportunities_by_deadline(
            dedupe_opportunities(await repo.list_all_public_active())
        )
    if limit is not None:
        entries = entries[:limit]

    pushed = failed = 0
    for entry in entries:
        ok = await push_catalog_opportunity_by_id(entry.id, event=event)
        if ok:
            pushed += 1
        else:
            failed += 1
        await asyncio.sleep(0.05)
    return {"pushed": pushed, "failed": failed, "skipped": 0, "total": len(entries)}


async def run_startify_catalog_sync_forever(interval_seconds: int | None = None) -> None:
    """Periodic full sync so Startify stays up to date without manual /push_startify."""
    settings = get_settings()
    interval = (
        interval_seconds
        if interval_seconds is not None
        else int(settings.startify_catalog_sync_interval_seconds)
    )
    if interval <= 0:
        logger.info("Startify catalog periodic sync disabled (interval=%s)", interval)
        return

    # First run shortly after boot — catch anything missed while webhook was down.
    await asyncio.sleep(90)
    while True:
        try:
            if not is_push_configured():
                logger.warning(
                    "Startify auto-sync skipped: set PARTNER_API_KEY + STARTIFY_CATALOG_WEBHOOK_URL"
                )
            else:
                stats = await push_all_active_catalog(event=EVENT_UPDATED)
                logger.info(
                    "Startify catalog auto-sync: total=%s pushed=%s failed=%s",
                    stats["total"],
                    stats["pushed"],
                    stats["failed"],
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Startify catalog auto-sync error: %s", exc)
        await asyncio.sleep(interval)

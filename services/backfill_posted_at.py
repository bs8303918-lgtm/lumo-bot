"""Backfill Telegram post dates for raw messages (posted_at)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from db.base import async_session_factory
from db.models import MonitoredChannel, RawMessage
from monitor.channel_resolver import ChannelResolver
from monitor.telethon_client import ensure_telethon_connected

logger = logging.getLogger(__name__)


async def backfill_posted_at(*, limit: int = 40) -> int:
    client = await ensure_telethon_connected()
    if not await client.is_user_authorized():
        return 0

    async with async_session_factory() as session:
        result = await session.execute(
            select(RawMessage, MonitoredChannel.channel_identifier)
            .join(MonitoredChannel, RawMessage.monitored_channel_id == MonitoredChannel.id)
            .where(RawMessage.posted_at.is_(None))
            .order_by(RawMessage.id.desc())
            .limit(limit)
        )
        rows = list(result.all())

    if not rows:
        return 0

    resolver = ChannelResolver(client)
    updated = 0
    entity_cache: dict[str, object] = {}

    for raw_message, channel_identifier in rows:
        try:
            entity = entity_cache.get(channel_identifier)
            if entity is None:
                entity = await client.get_entity(channel_identifier)
                entity_cache[channel_identifier] = entity

            tg_message = await client.get_messages(entity, ids=raw_message.telegram_message_id)
            if not tg_message or not getattr(tg_message, "date", None):
                continue

            posted_at = tg_message.date
            if posted_at.tzinfo is None:
                from datetime import timezone

                posted_at = posted_at.replace(tzinfo=timezone.utc)

            async with async_session_factory() as session:
                row = await session.execute(
                    select(RawMessage)
                    .options(joinedload(RawMessage.monitored_channel))
                    .where(RawMessage.id == raw_message.id)
                )
                msg = row.scalar_one_or_none()
                if msg and msg.posted_at is None:
                    msg.posted_at = posted_at
                    await session.commit()
                    updated += 1
        except Exception as exc:
            logger.debug(
                "backfill posted_at skip message %s (%s): %s",
                raw_message.id,
                channel_identifier,
                exc,
            )

    if updated:
        logger.info("Backfilled posted_at for %d messages", updated)
    return updated


async def backfill_posted_at_batches(*, batch_size: int = 40, max_batches: int = 20) -> int:
    """Fill missing Telegram post dates in batches (e.g. on startup)."""
    total = 0
    for _ in range(max_batches):
        updated = await backfill_posted_at(limit=batch_size)
        total += updated
        if updated == 0:
            break
    return total

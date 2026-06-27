import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from telethon.errors import ChannelPrivateError, FloodWaitError, UsernameNotOccupiedError

from config import get_settings
from db.base import async_session_factory
from db.models import RawMessage
from db.repositories.channels import ChannelRepository
from db.repositories.users import EventRepository, MessageRepository, SystemStateRepository
from logging_setup import log_error
from monitor.channel_resolver import ChannelResolver
from monitor.telethon_client import ensure_telethon_connected
from services.admin_notify import notify_admin
from services.channel_service import sync_seed_channels

logger = logging.getLogger(__name__)

BATCH_COMMIT_SIZE = 50


@dataclass
class FetchedMessage:
    telegram_message_id: int
    text: str
    message_link: str
    posted_at: datetime | None = None


class MonitorWorker:
    def __init__(self):
        self.settings = get_settings()
        self._running = False

    async def run_cycle(self) -> None:
        client = await ensure_telethon_connected()
        if not await client.is_user_authorized():
            logger.error("Telethon session not authorized, skipping monitor cycle")
            async with async_session_factory() as session:
                state_repo = SystemStateRepository(session)
                await state_repo.set("telethon_session_ok", "false")
                await session.commit()
            return

        resolver = ChannelResolver(client)
        await sync_seed_channels()

        async with async_session_factory() as session:
            channel_repo = ChannelRepository(session)
            state_repo = SystemStateRepository(session)
            stale = await channel_repo.cleanup_inaccessible_user_channels()
            if stale:
                await EventRepository(session).log(
                    "channels_purged",
                    metadata={"channels": stale, "reason": "inaccessible_cleanup"},
                )
                logger.info("Purged %d stale inaccessible channels: %s", len(stale), ", ".join(stale))
            channels = await channel_repo.get_monitored_channels()
            await state_repo.set("telethon_session_ok", "true")
            await session.commit()

        names = ", ".join(ch.channel_identifier for ch in channels) or "—"
        logger.info("Monitor cycle: %d channels to check — %s", len(channels), names)
        errors = 0
        channel_jobs = [(ch.id, ch.channel_identifier) for ch in channels]

        for channel_id, channel_identifier in channel_jobs:
            try:
                await self._process_channel(client, resolver, channel_id)
            except FloodWaitError as exc:
                log_error(
                    logger,
                    "monitor_worker",
                    exc,
                    {"channel": channel_identifier, "seconds": exc.seconds},
                )
                async with async_session_factory() as session:
                    await EventRepository(session).log(
                        "telethon_flood_wait",
                        metadata={"channel": channel_identifier, "seconds": exc.seconds},
                    )
                    await session.commit()
                await asyncio.sleep(exc.seconds)
            except Exception as exc:
                errors += 1
                log_error(logger, "monitor_worker", exc, {"channel": channel_identifier})

            await asyncio.sleep(self.settings.telethon_request_delay_seconds)

        async with async_session_factory() as session:
            state_repo = SystemStateRepository(session)
            event_repo = EventRepository(session)
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            posts_today = await session.execute(
                select(func.count()).select_from(RawMessage).where(RawMessage.fetched_at >= today_start)
            )
            posts_count = int(posts_today.scalar_one())
            if errors == 0 or errors < len(channels):
                await state_repo.set("last_monitor_success_at", datetime.now(timezone.utc).isoformat())
                await state_repo.reset("monitor_fail_streak")
                await event_repo.log(
                    "monitor_cycle_success",
                    metadata={"channels": len(channels), "errors": errors, "postsToday": posts_count},
                )
            else:
                streak = int(await state_repo.get("monitor_fail_streak", "0") or 0) + 1
                await state_repo.set("monitor_fail_streak", str(streak))
                await event_repo.log("monitor_cycle_error", metadata={"streak": streak})
                if streak >= 2:
                    await notify_admin(f"⚠️ Lumo: мониторинг не прошёл {streak} циклов подряд.")
            await session.commit()

        async with async_session_factory() as session:
            removed = await MessageRepository(session).purge_expired_unmatched()
            if removed:
                await session.commit()
                logger.info("Purged %d expired unmatched posts", removed)

        try:
            from services.daily_digest import run_daily_digests_for_all_users
            from services.notification_service import NotificationService

            await run_daily_digests_for_all_users(NotificationService())
        except Exception as exc:
            log_error(logger, "daily_digest", exc)

    async def scan_channel(self, channel_db_id: int) -> int:
        """Сканировать один канал сразу (например, после /add_channel)."""
        client = await ensure_telethon_connected()
        if not await client.is_user_authorized():
            logger.warning("Telethon not authorized, skip immediate channel scan")
            return 0
        resolver = ChannelResolver(client)
        await self._process_channel(client, resolver, channel_db_id)
        return 0

    async def _save_messages(
        self,
        channel_db_id: int,
        identifier: str,
        entity,
        fetched: list[FetchedMessage],
        new_max_id: int,
    ) -> int:
        from sqlalchemy import select
        from db.models import MonitoredChannel

        if new_max_id > 0:
            async with async_session_factory() as session:
                channel_repo = ChannelRepository(session)
                result = await session.execute(select(MonitoredChannel).where(MonitoredChannel.id == channel_db_id))
                channel = result.scalar_one()
                await channel_repo.update_monitored_cursor(channel, new_max_id)
                if getattr(entity, "title", None):
                    channel.channel_title = entity.title
                if getattr(entity, "id", None):
                    channel.telegram_channel_id = entity.id
                await session.commit()

        if not fetched:
            return 0

        new_count = 0
        for offset in range(0, len(fetched), BATCH_COMMIT_SIZE):
            batch = fetched[offset : offset + BATCH_COMMIT_SIZE]
            async with async_session_factory() as session:
                channel_repo = ChannelRepository(session)
                result = await session.execute(select(MonitoredChannel).where(MonitoredChannel.id == channel_db_id))
                channel = result.scalar_one()
                for item in batch:
                    created, _ = await channel_repo.save_raw_message(
                        channel.id,
                        item.telegram_message_id,
                        item.text,
                        item.message_link,
                        posted_at=item.posted_at,
                    )
                    if created:
                        new_count += 1
                await session.commit()

        if new_count:
            logger.info("Channel %s: %d new messages", identifier, new_count)
            async with async_session_factory() as session:
                await EventRepository(session).log(
                    "channel_scan",
                    metadata={"channel": identifier, "newPosts": new_count},
                )
                await session.commit()
        return new_count

    async def _mark_channel_unavailable(
        self,
        channel_repo: ChannelRepository,
        channel,
        identifier: str,
        session,
        *,
        reason: str,
    ) -> None:
        if not channel.is_seed:
            await channel_repo.set_channel_inaccessible(channel)
            await session.commit()
        async with async_session_factory() as log_session:
            await EventRepository(log_session).log(
                "channel_unavailable",
                metadata={"channel": identifier, "retryIn": "1ч", "reason": reason},
            )
            await log_session.commit()
        logger.warning("Channel %s unavailable (%s)", identifier, reason)

    async def _mark_channel_missing(
        self,
        channel_repo: ChannelRepository,
        channel,
        identifier: str,
        session,
    ) -> None:
        if channel.is_seed:
            logger.warning("Seed channel %s not found, will retry next cycle", identifier)
            return

        stats = await channel_repo.purge_dead_channel(identifier)
        await session.commit()
        async with async_session_factory() as log_session:
            await EventRepository(log_session).log(
                "channel_removed",
                metadata={
                    "channel": identifier,
                    "reason": "username_not_found",
                    "removed_users": stats.get("removed_users", 0),
                    "source": "monitor",
                },
            )
            await log_session.commit()
        logger.info(
            "Channel %s not found — removed from monitoring (%d user subscriptions)",
            identifier,
            stats.get("removed_users", 0),
        )

    async def _process_channel(self, client, resolver: ChannelResolver, channel_db_id: int) -> None:
        from sqlalchemy import select
        from db.models import MonitoredChannel

        async with async_session_factory() as session:
            channel_repo = ChannelRepository(session)
            result = await session.execute(select(MonitoredChannel).where(MonitoredChannel.id == channel_db_id))
            channel = result.scalar_one()
            identifier = channel.channel_identifier
            is_first_scan = channel.last_checked_message_id is None
            min_id = channel.last_checked_message_id

            try:
                entity = await client.get_entity(identifier)
            except ChannelPrivateError:
                await self._mark_channel_unavailable(channel_repo, channel, identifier, session, reason="private")
                return
            except UsernameNotOccupiedError:
                await self._mark_channel_missing(channel_repo, channel, identifier, session)
                return
            except ValueError as exc:
                if "username" in str(exc).lower() or "no user has" in str(exc).lower():
                    await self._mark_channel_missing(channel_repo, channel, identifier, session)
                    return
                raise
            await session.commit()

        if is_first_scan:
            limit = self.settings.monitor_initial_posts_limit
            recent = await client.get_messages(entity, limit=limit)
            if not recent:
                async with async_session_factory() as session:
                    channel_repo = ChannelRepository(session)
                    result = await session.execute(select(MonitoredChannel).where(MonitoredChannel.id == channel_db_id))
                    channel = result.scalar_one()
                    await channel_repo.update_monitored_cursor(channel, 0)
                    await session.commit()
                logger.info("Channel %s: empty channel, cursor initialized", identifier)
                return

            new_max_id = max(m.id for m in recent)
            cutoff = datetime.now(timezone.utc) - timedelta(days=self.settings.monitor_initial_max_age_days)
            fetched: list[FetchedMessage] = []
            skipped_old = 0
            skipped_no_text = 0
            for message in sorted(recent, key=lambda m: m.id):
                if not message.message:
                    skipped_no_text += 1
                    continue
                msg_date = message.date
                if msg_date is None:
                    skipped_old += 1
                    continue
                if msg_date.tzinfo is None:
                    msg_date = msg_date.replace(tzinfo=timezone.utc)
                if msg_date < cutoff:
                    skipped_old += 1
                    continue
                link = resolver.build_message_link(identifier, message.id)
                fetched.append(FetchedMessage(message.id, message.message, link, msg_date))

            await self._save_messages(channel_db_id, identifier, entity, fetched, new_max_id)
            logger.info(
                "Channel %s: first join — last %d posts, saved %d (skipped %d old, %d without text/date)",
                identifier,
                len(recent),
                len(fetched),
                skipped_old,
                skipped_no_text,
            )
            return

        if min_id is None:
            return

        fetched = []
        new_max_id = min_id
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.settings.monitor_initial_max_age_days)
        skipped_old = 0
        async for message in client.iter_messages(entity, min_id=min_id, reverse=True):
            new_max_id = max(new_max_id, message.id)
            if not message.message:
                continue
            msg_date = message.date
            if msg_date is None:
                skipped_old += 1
                continue
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            if msg_date < cutoff:
                skipped_old += 1
                continue
            link = resolver.build_message_link(identifier, message.id)
            fetched.append(FetchedMessage(message.id, message.message, link, msg_date))

        if skipped_old:
            logger.info(
                "Channel %s: skipped %d non-new/old messages (only id>%s, max age %d days)",
                identifier,
                skipped_old,
                min_id,
                self.settings.monitor_initial_max_age_days,
            )

        await self._save_messages(channel_db_id, identifier, entity, fetched, new_max_id)

    async def run_forever(self) -> None:
        self._running = True
        interval = self.settings.monitor_interval_minutes * 60
        while self._running:
            try:
                await self.run_cycle()
            except Exception as exc:
                log_error(logger, "monitor_worker", exc)
                async with async_session_factory() as session:
                    streak = int(await SystemStateRepository(session).get("monitor_fail_streak", "0") or 0) + 1
                    await SystemStateRepository(session).set("monitor_fail_streak", str(streak))
                    await session.commit()
                    if streak >= 2:
                        await notify_admin(f"⚠️ Lumo: воркер мониторинга упал: {exc}")
            await asyncio.sleep(interval)

    def stop(self) -> None:
        self._running = False

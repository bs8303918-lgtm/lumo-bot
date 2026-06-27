from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import MonitoredChannel, SeedChannel, User, UserChannel
from db.repositories.users import normalize_channel_identifier


class ChannelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_user_channels(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(UserChannel).where(UserChannel.user_id == user_id)
        )
        return result.scalar_one()

    async def get_user_channels(self, user_id: int) -> list[UserChannel]:
        result = await self.session.execute(
            select(UserChannel).where(UserChannel.user_id == user_id).order_by(UserChannel.added_at)
        )
        return list(result.scalars().all())

    async def user_has_channel(self, user_id: int, channel_identifier: str) -> bool:
        identifier = normalize_channel_identifier(channel_identifier)
        result = await self.session.execute(
            select(UserChannel.id).where(
                UserChannel.user_id == user_id,
                UserChannel.channel_identifier == identifier,
            )
        )
        return result.scalar_one_or_none() is not None

    async def add_user_channel(
        self, user_id: int, channel_identifier: str, channel_title: str | None = None
    ) -> UserChannel:
        identifier = normalize_channel_identifier(channel_identifier)
        uc = UserChannel(
            user_id=user_id,
            channel_identifier=identifier,
            channel_title=channel_title,
        )
        self.session.add(uc)
        await self.session.flush()
        await self._ensure_monitored(identifier, channel_title=channel_title, is_seed=False, increment_source=True)
        return uc

    async def remove_user_channel(self, user_id: int, channel_id: int) -> str | None:
        result = await self.session.execute(
            select(UserChannel).where(UserChannel.id == channel_id, UserChannel.user_id == user_id)
        )
        uc = result.scalar_one_or_none()
        if not uc:
            return None
        identifier = uc.channel_identifier
        await self.session.delete(uc)
        await self.session.flush()
        await self._decrement_or_remove_monitored(identifier)
        return identifier

    async def get_monitored_channels(self) -> list[MonitoredChannel]:
        result = await self.session.execute(
            select(MonitoredChannel).where(MonitoredChannel.is_accessible.is_(True)).order_by(MonitoredChannel.id)
        )
        return list(result.scalars().all())

    async def get_monitored_by_identifier(self, identifier: str) -> MonitoredChannel | None:
        identifier = normalize_channel_identifier(identifier)
        result = await self.session.execute(
            select(MonitoredChannel).where(MonitoredChannel.channel_identifier == identifier)
        )
        return result.scalar_one_or_none()

    async def update_monitored_cursor(
        self, channel: MonitoredChannel, last_message_id: int, success: bool = True
    ) -> None:
        channel.last_checked_message_id = last_message_id
        channel.last_checked_at = datetime.now(timezone.utc)
        if success:
            channel.last_success_at = datetime.now(timezone.utc)

    async def set_channel_inaccessible(self, channel: MonitoredChannel) -> None:
        if channel.is_seed:
            return
        channel.is_accessible = False

    async def count_monitored(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(MonitoredChannel))
        return result.scalar_one()

    async def avg_channels_per_user(self) -> float:
        total = await self.session.execute(select(func.count()).select_from(UserChannel))
        users = await self.session.execute(select(func.count(func.distinct(UserChannel.user_id))))
        user_count = users.scalar_one()
        if user_count == 0:
            return 0.0
        return round(total.scalar_one() / user_count, 2)

    async def list_user_channels_with_owners(self) -> list[tuple[UserChannel, User]]:
        result = await self.session.execute(
            select(UserChannel, User)
            .join(User, UserChannel.user_id == User.id)
            .order_by(User.username.nulls_last(), User.telegram_id, UserChannel.added_at)
        )
        return list(result.all())

    async def list_user_added_monitored(self) -> list[MonitoredChannel]:
        """Monitored channels added by users (not seed-only)."""
        result = await self.session.execute(
            select(MonitoredChannel)
            .where(MonitoredChannel.is_seed.is_(False))
            .where(MonitoredChannel.source_count > 0)
            .order_by(MonitoredChannel.channel_identifier)
        )
        return list(result.scalars().all())

    async def _ensure_monitored(
        self,
        identifier: str,
        channel_title: str | None = None,
        is_seed: bool = False,
        increment_source: bool = False,
    ) -> MonitoredChannel:
        identifier = normalize_channel_identifier(identifier)
        existing = await self.get_monitored_by_identifier(identifier)
        if existing:
            if channel_title and not existing.channel_title:
                existing.channel_title = channel_title
            if is_seed:
                existing.is_seed = True
            if increment_source:
                existing.source_count += 1
            return existing

        ch = MonitoredChannel(
            channel_identifier=identifier,
            channel_title=channel_title,
            is_seed=is_seed,
            source_count=1 if increment_source else 0,
        )
        self.session.add(ch)
        await self.session.flush()
        return ch

    async def _decrement_or_remove_monitored(self, identifier: str) -> None:
        identifier = normalize_channel_identifier(identifier)
        ch = await self.get_monitored_by_identifier(identifier)
        if not ch:
            return
        if ch.is_seed:
            if ch.source_count > 0:
                ch.source_count -= 1
            return
        ch.source_count = max(0, ch.source_count - 1)
        if ch.source_count <= 0:
            await self._delete_monitored_channel(ch)

    async def _delete_monitored_channel(self, ch: MonitoredChannel) -> None:
        from db.models import CatalogOpportunity, ProcessedPair, RawMessage, SentMatch

        channel_id = ch.id
        raw_ids_result = await self.session.execute(
            select(RawMessage.id).where(RawMessage.monitored_channel_id == channel_id)
        )
        raw_ids = [row[0] for row in raw_ids_result.all()]
        if raw_ids:
            await self.session.execute(
                delete(SentMatch).where(SentMatch.raw_message_id.in_(raw_ids))
            )
            await self.session.execute(
                delete(ProcessedPair).where(ProcessedPair.raw_message_id.in_(raw_ids))
            )
            await self.session.execute(
                delete(CatalogOpportunity).where(CatalogOpportunity.raw_message_id.in_(raw_ids))
            )
            await self.session.execute(
                delete(RawMessage).where(RawMessage.monitored_channel_id == channel_id)
            )
        await self.session.execute(
            delete(MonitoredChannel).where(MonitoredChannel.id == channel_id)
        )
        await self.session.flush()
        self.session.expunge(ch)

    async def purge_dead_channel(self, identifier: str) -> dict[str, int | bool]:
        """Удалить несуществующий канал у всех пользователей и из monitored_channels."""
        identifier = normalize_channel_identifier(identifier)
        ch = await self.get_monitored_by_identifier(identifier)
        if not ch or ch.is_seed:
            return {"removed_users": 0, "monitored_deleted": False}

        uc_result = await self.session.execute(
            delete(UserChannel).where(UserChannel.channel_identifier == identifier)
        )
        removed_users = uc_result.rowcount or 0
        await self._delete_monitored_channel(ch)
        return {"removed_users": removed_users, "monitored_deleted": True}

    async def cleanup_inaccessible_user_channels(self) -> list[str]:
        """Убрать из мониторинга пользовательские каналы, уже помеченные недоступными."""
        result = await self.session.execute(
            select(MonitoredChannel.channel_identifier).where(
                MonitoredChannel.is_seed.is_(False),
                MonitoredChannel.is_accessible.is_(False),
            )
        )
        removed: list[str] = []
        for (identifier,) in result.all():
            stats = await self.purge_dead_channel(identifier)
            if stats.get("monitored_deleted"):
                removed.append(identifier)
        return removed

    async def upsert_seed_channel(self, identifier: str, channel_title: str | None = None) -> SeedChannel:
        identifier = normalize_channel_identifier(identifier)
        result = await self.session.execute(
            select(SeedChannel).where(SeedChannel.channel_identifier == identifier)
        )
        seed = result.scalar_one_or_none()
        if seed:
            if channel_title:
                seed.channel_title = channel_title
            seed.is_active = True
        else:
            seed = SeedChannel(channel_identifier=identifier, channel_title=channel_title)
            self.session.add(seed)
        await self.session.flush()
        await self._ensure_monitored(identifier, channel_title=channel_title, is_seed=True, increment_source=False)
        return seed

    async def get_active_seed_channels(self) -> list[SeedChannel]:
        result = await self.session.execute(
            select(SeedChannel).where(SeedChannel.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def save_raw_message(
        self,
        monitored_channel_id: int,
        telegram_message_id: int,
        text: str,
        message_link: str,
        *,
        posted_at: datetime | None = None,
    ) -> tuple[bool, int | None]:
        from db.models import RawMessage

        result = await self.session.execute(
            select(RawMessage).where(
                RawMessage.monitored_channel_id == monitored_channel_id,
                RawMessage.telegram_message_id == telegram_message_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if posted_at is not None and existing.posted_at is None:
                existing.posted_at = posted_at
                await self.session.flush()
            return False, existing.id

        msg = RawMessage(
            monitored_channel_id=monitored_channel_id,
            telegram_message_id=telegram_message_id,
            text=text,
            message_link=message_link,
            posted_at=posted_at,
        )
        self.session.add(msg)
        await self.session.flush()
        return True, msg.id

    async def purge_channel_feed(self, channel_identifier: str) -> dict[str, int | str]:
        """Деактивировать каталог и очистить матчи по пользовательскому каналу."""
        from db.models import CatalogOpportunity, ProcessedPair, RawMessage, SentMatch

        identifier = normalize_channel_identifier(channel_identifier)
        ch = await self.get_monitored_by_identifier(identifier)
        if not ch:
            return {"error": "not_found"}
        if ch.is_seed:
            return {"error": "seed_channel"}

        raw_ids_result = await self.session.execute(
            select(RawMessage.id).where(RawMessage.monitored_channel_id == ch.id)
        )
        raw_ids = [row[0] for row in raw_ids_result.all()]
        if not raw_ids:
            return {"catalog": 0, "sent": 0, "processed": 0}

        catalog_n = 0
        cat_result = await self.session.execute(
            select(CatalogOpportunity).where(CatalogOpportunity.raw_message_id.in_(raw_ids))
        )
        for entry in cat_result.scalars():
            if entry.is_active:
                entry.is_active = False
                catalog_n += 1

        sent_result = await self.session.execute(
            delete(SentMatch).where(SentMatch.raw_message_id.in_(raw_ids))
        )
        processed_result = await self.session.execute(
            delete(ProcessedPair).where(ProcessedPair.raw_message_id.in_(raw_ids))
        )
        return {
            "catalog": catalog_n,
            "sent": sent_result.rowcount or 0,
            "processed": processed_result.rowcount or 0,
        }

from pathlib import Path

from sqlalchemy import update

from config import get_settings
from db.base import async_session_factory
from db.models import MonitoredChannel
from db.repositories.channels import ChannelRepository
from db.repositories.users import normalize_channel_identifier
from monitor.channel_resolver import ChannelResolver
from monitor.telethon_client import require_authorized_client


async def sync_seed_channels(file_path: Path | None = None) -> int:
    """Загрузить seed-каналы из файла, включить мониторинг для всех."""
    settings = get_settings()
    path = file_path or settings.seed_channels_file
    if not path.exists():
        return 0

    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return 0

    client = await require_authorized_client()
    resolver = ChannelResolver(client) if client else None
    synced = 0

    async with async_session_factory() as session:
        repo = ChannelRepository(session)
        for line in lines:
            identifier = normalize_channel_identifier(line)
            if resolver:
                info, _error = await resolver.validate_public_channel(identifier)
                if info:
                    await repo.upsert_seed_channel(info.identifier, info.title)
                    synced += 1
                    continue
            await repo.upsert_seed_channel(identifier)
            synced += 1

        await session.execute(
            update(MonitoredChannel)
            .where(MonitoredChannel.is_seed.is_(True))
            .values(is_accessible=True)
        )
        await session.commit()

    return synced


async def seed_channels_from_file(file_path: Path | None = None) -> int:
    return await sync_seed_channels(file_path)

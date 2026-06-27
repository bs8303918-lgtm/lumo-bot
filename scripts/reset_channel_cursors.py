"""Сбросить курсор каналов — при следующем цикле история снова не читается,
но уже сохранённые raw_messages останутся. Run: python scripts/reset_channel_cursors.py"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import update

from db.base import async_session_factory
from db.models import MonitoredChannel


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            update(MonitoredChannel).values(last_checked_message_id=None)
        )
        await session.commit()
        print(f"Курсоры сброшены у {result.rowcount} каналов.")
        print("При следующем цикле воркер пропустит историю и начнёт с последнего поста.")


if __name__ == "__main__":
    asyncio.run(main())

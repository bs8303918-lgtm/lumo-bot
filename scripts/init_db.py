import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.base import Base, engine
from db.migrations import ensure_user_columns
from services.channel_service import seed_channels_from_file


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_user_columns()
    count = await seed_channels_from_file()
    print(f"Database initialized. Seed channels: {count}")


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json

from sqlalchemy import select

from db.base import async_session_factory
from db.models import CatalogOpportunity


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(CatalogOpportunity).where(CatalogOpportunity.title.like("%AI%preneurs%"))
        )
        for entry in result.scalars():
            print(entry.id, entry.tags_json)


asyncio.run(main())

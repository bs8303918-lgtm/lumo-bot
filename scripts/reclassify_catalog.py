import asyncio

from db.base import async_session_factory
from db.repositories.opportunity_catalog import OpportunityCatalogRepository


async def main() -> None:
    async with async_session_factory() as session:
        n = await OpportunityCatalogRepository(session).reclassify_active_types()
        await session.commit()
    print("reclassified", n)


asyncio.run(main())

"""Reactivate catalog rows hidden by the old 7-day post-age cutoff."""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import get_settings
from db.base import async_session_factory
from db.repositories.opportunity_catalog import OpportunityCatalogRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reactivate_catalog")


async def main() -> None:
    settings = get_settings()
    async with async_session_factory() as session:
        repo = OpportunityCatalogRepository(
            session,
            no_deadline_max_age_days=settings.catalog_no_deadline_max_age_days,
        )
        expired = await repo.deactivate_expired()
        reactivated = await repo.reactivate_all_real_opportunities()
        await session.commit()
        logger.info("expired=%d reactivated=%d", len(expired), len(reactivated))
        if reactivated:
            try:
                from services.startify_catalog_push import schedule_catalog_push

                schedule_catalog_push(reactivated)
                await asyncio.sleep(3)
            except Exception as exc:
                logger.warning("Startify push skipped: %s", exc)

        active = await repo.count_active()
        by_type = await repo.count_active_by_type()
        logger.info("active_total=%d by_type=%s", active, by_type)


if __name__ == "__main__":
    asyncio.run(main())

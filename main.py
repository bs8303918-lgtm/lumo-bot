import asyncio
import logging

from bot.app import create_dispatcher
from bot.instance import close_bot, create_bot
from config import get_settings
from db.base import Base, async_session_factory, engine
from db.migrations import ensure_catalog_columns, ensure_raw_message_columns, ensure_user_columns
from llm.client import LLMClient
from llm.processor import LLMProcessor
from logging_setup import setup_logging
from monitor.retry import run_with_retry
from monitor.worker import MonitorWorker
from services.channel_service import seed_channels_from_file
from services.notification_service import NotificationService
from bot.webapp_setup import setup_telegram_webapp, sync_user_menu_button
from scripts.build_webapp import ensure_webapp_built
from services.http_server import run_api_server
from utils.instance_lock import acquire_instance_lock, release_instance_lock

logger = logging.getLogger(__name__)


async def init_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_user_columns()
    await ensure_raw_message_columns()
    await ensure_catalog_columns()

    async with async_session_factory() as session:
        from sqlalchemy import select

        from db.models import User
        from db.repositories.users import MatchRepository, MessageRepository, SystemStateRepository

        settings = get_settings()
        backfilled = await MatchRepository(session).backfill_processed_from_sent()
        if backfilled:
            await session.commit()
            logger.info("Backfilled %d processed_pairs from existing sent_matches", backfilled)

        msg_repo = MessageRepository(session)
        state_repo = SystemStateRepository(session)
        max_raw_id = await msg_repo.get_max_raw_message_id()
        result = await session.execute(select(User).where(User.interest_query.is_not(None)))
        users = list(result.scalars().all())
        initialized = 0
        for user in users:
            if await state_repo.get_llm_min_raw_id(user.id) is not None:
                continue
            floor = max(0, max_raw_id - settings.llm_reanalyze_recent_count)
            await state_repo.set_llm_min_raw_id(user.id, floor)
            initialized += 1
        if initialized:
            await session.commit()
            logger.info(
                "LLM queue trimmed for %d users — only messages id>%d will be analyzed",
                initialized,
                floor,
            )

        from services.opportunity_catalog import catalog_repo

        repo = catalog_repo(session)
        archived = await repo.archive_stale_unclassified(limit=500)
        expired = await repo.deactivate_expired()
        stale = await repo.deactivate_stale_without_deadline()
        old = await repo.deactivate_old_posts()
        invalid = await repo.deactivate_invalid_active()
        reclassified = await repo.reclassify_active_types()
        duplicates = await repo.deactivate_duplicates()
        if archived or expired or stale or old or invalid or reclassified or duplicates:
            await session.commit()
            logger.info(
                "Catalog cleanup on startup: archived=%d expired=%d stale=%d old_posts=%d invalid=%d reclassified=%d duplicates=%d",
                archived,
                expired,
                stale,
                old,
                invalid,
                reclassified,
                duplicates,
            )


async def run_bot(bot) -> None:
    settings = get_settings()
    dp = create_dispatcher()
    await dp.start_polling(
        bot,
        polling_timeout=settings.bot_polling_timeout_seconds,
        close_bot_session=False,
    )


async def run_posted_at_backfill() -> None:
    """Fill missing post dates in the background — must not block bot/API startup."""
    while True:
        try:
            from services.backfill_posted_at import backfill_posted_at

            updated = await backfill_posted_at(limit=25)
            await asyncio.sleep(300 if updated == 0 else 45)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("posted_at backfill: %s", exc)
            await asyncio.sleep(120)


async def run_monitor() -> None:
    worker = MonitorWorker()

    async def cycle():
        await worker.run_forever()

    await run_with_retry("monitor_worker", cycle, on_critical=_on_monitor_critical)


async def run_llm_processor() -> None:
    processor = LLMProcessor(NotificationService())

    async def cycle():
        await processor.run_forever()

    await run_with_retry("llm_processor", cycle)


async def _on_monitor_critical(exc: Exception) -> None:
    from services.admin_notify import notify_admin

    await notify_admin(f"🚨 Lumo: воркер мониторинга не восстановился: {exc}")


async def _setup_webapp(bot) -> None:
    settings = get_settings()
    await setup_telegram_webapp(bot)
    if settings.telegram_admin_chat_id:
        await sync_user_menu_button(bot, settings.telegram_admin_chat_id)
    url = settings.resolved_webapp_url
    if url:
        logger.info("Mini App URL: %s", url)
    elif settings.is_bot_polling:
        logger.warning(
            "Mini App URL не задан — кнопка Open не появится. "
            "Укажи PUBLIC_BASE_URL (Railway domain) в переменных окружения."
        )


async def main() -> None:
    setup_logging()
    settings = get_settings()
    mode = settings.lumo_mode.lower()
    use_lock = mode == "full" and not settings.skip_instance_lock and not settings.is_railway

    if use_lock:
        acquire_instance_lock()

    logger.info("Starting Lumo (mode=%s)...", mode)
    logger.info("LLM provider: %s, model: %s", settings.llm_provider, settings.llm_model_name)

    bot = None
    try:
        await init_database()
        seeded = await seed_channels_from_file()
        logger.info("Seed channels loaded: %d", seeded)

        if settings.auto_build_webapp and settings.serve_mini_app:
            ensure_webapp_built()

        tasks: list = []

        if settings.is_worker:
            tasks.extend(
                [
                    run_monitor(),
                    run_llm_processor(),
                    run_api_server(),
                    run_posted_at_backfill(),
                ]
            )

        if settings.is_bot_polling:
            bot = create_bot()
            await _setup_webapp(bot)
            tasks.append(run_bot(bot))
        elif settings.telegram_bot_token:
            bot = create_bot()
            await _setup_webapp(bot)

        if not tasks:
            raise SystemExit("Nothing to run — set LUMO_MODE to full, worker, or bot")

        await asyncio.gather(*tasks)
    finally:
        await LLMClient.close_http()
        if bot is not None:
            await close_bot()
        if use_lock:
            release_instance_lock()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")

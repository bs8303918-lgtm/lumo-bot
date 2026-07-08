import asyncio
import logging
from pathlib import Path

from bot.app import create_dispatcher
from bot.instance import close_bot, create_bot
from config import get_settings
from db.base import Base, async_session_factory, configure_supabase_pooler, engine
from db.migrations import (
    ensure_catalog_multi_per_message,
    ensure_google_auth_columns,
    ensure_raw_message_columns,
    ensure_subscription_columns,
    ensure_user_columns,
    ensure_web_auth_columns,
)
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


async def init_schema() -> None:
    """Быстро: схема + миграции — не блокирует healthcheck."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        settings = get_settings()
        db_hint = settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url[:60]
        logger.error(
            "Database connection failed (%s). Check DATABASE_URL on Railway: "
            "Supabase pooler, redeploy after change. Host: %s",
            type(exc).__name__,
            db_hint,
        )
        raise
    await ensure_user_columns()
    await ensure_raw_message_columns()
    await ensure_catalog_multi_per_message()
    await ensure_subscription_columns()
    await ensure_google_auth_columns()
    await ensure_web_auth_columns()


async def run_startup_maintenance() -> None:
    """Тяжёлая фоновая работа после старта API — backfill, чистка каталога."""
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
        floor = 0
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
        archived = await repo.archive_stale_unclassified(limit=200)
        expired = await repo.deactivate_expired()
        stale = await repo.deactivate_stale_without_deadline()
        old = await repo.deactivate_old_posts()
        invalid = await repo.deactivate_invalid_active()
        reclassified = await repo.reclassify_active_types()
        duplicates = await repo.deactivate_duplicates()
        if archived or expired or stale or old or invalid or reclassified or duplicates:
            await session.commit()
            logger.info(
                "Catalog cleanup: archived=%d expired=%d stale=%d old=%d invalid=%d reclassified=%d dup=%d",
                archived,
                expired,
                stale,
                old,
                invalid,
                reclassified,
                duplicates,
            )


async def init_database() -> None:
    """Полная инициализация (локально / однопроцессный режим)."""
    await init_schema()
    await run_startup_maintenance()


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
    from monitor.telethon_client import telethon_credentials_configured

    warned_missing = False
    while True:
        try:
            if not telethon_credentials_configured():
                if not warned_missing:
                    logger.warning(
                        "posted_at backfill skipped: TELEGRAM_API_ID / TELEGRAM_API_HASH not set"
                    )
                    warned_missing = True
                await asyncio.sleep(600)
                continue

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


async def run_subscription_reminders() -> None:
    from services.subscription_reminders import run_subscription_reminders_forever

    await run_subscription_reminders_forever()


async def _on_monitor_critical(exc: Exception) -> None:
    from services.admin_notify import notify_admin

    await notify_admin(f"🚨 Lumo: воркер мониторинга не восстановился: {exc}")


async def _run_after_boot(boot_ready: asyncio.Event, coro_fn, *, name: str = "worker") -> None:
    await boot_ready.wait()
    try:
        await coro_fn()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("%s crashed: %s", name, exc)


async def boot(boot_ready: asyncio.Event) -> None:
    try:
        await init_schema()
    except Exception as exc:
        logger.error("Schema init failed (API stays up, retry on next deploy): %s", exc)
    boot_ready.set()
    logger.info("Boot gate open — API/workers may start")
    try:
        try:
            seeded = await seed_channels_from_file()
        except Exception as exc:
            logger.warning("Seed channels skipped: %s", exc)
            seeded = 0
        logger.info("Seed channels loaded: %d", seeded)

        if settings.auto_build_webapp and settings.serve_mini_app:
            ensure_webapp_built()

        if settings.is_api_only:
            logger.info("API-only mode — skipping monitor/LLM maintenance")
            return

        await run_startup_maintenance()
        logger.info("Startup maintenance complete")
    except Exception as exc:
        logger.warning("Startup maintenance failed: %s", exc)


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


async def _run_bot_after_boot(boot_ready: asyncio.Event, bot_ref: list) -> None:
    await boot_ready.wait()
    try:
        bot = create_bot()
        bot_ref.append(bot)
        await _setup_webapp(bot)
        await run_bot(bot)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("Bot polling crashed: %s", exc)


async def _setup_bot_only(boot_ready: asyncio.Event, bot_ref: list) -> None:
    await boot_ready.wait()
    try:
        bot = create_bot()
        bot_ref.append(bot)
        await _setup_webapp(bot)
    except Exception as exc:
        logger.error("Bot setup failed: %s", exc)


async def _run_posted_at_after_boot(boot_ready: asyncio.Event) -> None:
    await boot_ready.wait()
    try:
        await run_posted_at_backfill()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("posted_at backfill crashed: %s", exc)


async def main() -> None:
    setup_logging()
    settings = get_settings()
    mode = settings.lumo_mode.lower()
    use_lock = mode == "full" and not settings.skip_instance_lock and not settings.is_railway

    if use_lock:
        acquire_instance_lock()

    logger.info(
        "Starting Lumo (mode=%s, railway=%s, api_only=%s)...",
        mode,
        settings.is_railway,
        settings.is_api_only,
    )
    if settings.is_railway and settings.is_bot_polling:
        logger.info("Telegram bot polling enabled on Railway")
    if settings.is_worker:
        from monitor.telethon_client import telethon_credentials_configured

        if telethon_credentials_configured():
            logger.info("Telethon credentials: configured (api_id=%s)", settings.telegram_api_id)
            if settings.telethon_session_string.strip():
                logger.info("Telethon session: TELETHON_SESSION_STRING (env, redeploy-safe)")
            else:
                session_file = Path(str(settings.resolved_telethon_session_path) + ".session")
                logger.info(
                    "Telethon session file: %s (exists=%s, size=%s bytes)",
                    session_file,
                    session_file.is_file(),
                    session_file.stat().st_size if session_file.is_file() else 0,
                )
                if settings.is_railway and not session_file.is_file():
                    logger.warning(
                        "Telethon session missing — export locally: "
                        "python scripts/export_telethon_session.py → TELETHON_SESSION_STRING in Railway"
                    )
        else:
            logger.error(
                "Telethon credentials MISSING — monitor/backfill disabled until you set "
                "TELEGRAM_API_ID and TELEGRAM_API_HASH in Railway Variables and redeploy"
            )
    logger.info("LLM provider: %s, model: %s", settings.llm_provider, settings.llm_model_name)

    try:
        await configure_supabase_pooler()
    except Exception as exc:
        logger.error("Supabase pooler probe failed: %s", exc)

    bot_ref: list = []
    try:
        boot_ready = asyncio.Event()
        tasks: list = []

        run_api = settings.api_enabled or (
            settings.is_railway and settings.lumo_mode.lower() != "bot"
        )
        if run_api:
            tasks.append(run_api_server())

        tasks.append(boot(boot_ready))

        if settings.is_worker and not settings.is_api_only:
            tasks.extend(
                [
                    _run_after_boot(boot_ready, run_monitor, name="monitor"),
                    _run_after_boot(boot_ready, run_llm_processor, name="llm"),
                    _run_after_boot(boot_ready, run_subscription_reminders, name="subscription_reminders"),
                    _run_posted_at_after_boot(boot_ready),
                ]
            )

        if settings.is_bot_polling:
            tasks.append(_run_bot_after_boot(boot_ready, bot_ref))
        elif settings.telegram_bot_token and not settings.is_api_only:
            tasks.append(_setup_bot_only(boot_ready, bot_ref))

        if not tasks:
            raise SystemExit("Nothing to run — set LUMO_MODE to full, worker, api, or bot")

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for idx, result in enumerate(results):
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                logger.error("Task %s failed: %s", idx, result)
    finally:
        await LLMClient.close_http()
        if bot_ref:
            await close_bot(bot_ref[0])
        if use_lock:
            release_instance_lock()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")

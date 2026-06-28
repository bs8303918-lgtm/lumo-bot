from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from config import get_settings


class Base(DeclarativeBase):
    pass


def _uses_supabase_pooler(database_url: str) -> bool:
    return "pooler.supabase.com" in database_url


def _is_supabase_host(database_url: str) -> bool:
    return _uses_supabase_pooler(database_url) or (
        "supabase.co" in database_url and "postgresql" in database_url
    )


def _postgres_connect_args(database_url: str) -> dict:
    """asyncpg SSL + Supabase (direct или pooler)."""
    import ssl

    args: dict = {}
    pooler = _uses_supabase_pooler(database_url)
    supabase = _is_supabase_host(database_url)
    if supabase:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        args["ssl"] = ctx
        args["command_timeout"] = 60
        args["timeout"] = 15
    elif "railway.internal" in database_url:
        pass
    else:
        args["ssl"] = True

    if pooler and ":6543" in database_url:
        args["statement_cache_size"] = 0

    return args


def _engine_kwargs_for_url(database_url: str) -> dict:
    kwargs: dict = {
        "echo": False,
        "pool_pre_ping": True,
    }
    settings = get_settings()
    if settings.is_sqlite:
        kwargs["connect_args"] = {"timeout": 30}
        kwargs["poolclass"] = NullPool
    elif database_url.startswith("postgresql"):
        kwargs["connect_args"] = _postgres_connect_args(database_url)
        if _uses_supabase_pooler(database_url) and ":6543" in database_url:
            kwargs["poolclass"] = NullPool
        else:
            kwargs["pool_size"] = 10
            kwargs["max_overflow"] = 10
    return kwargs


def _register_engine_events(db_engine) -> None:
    @event.listens_for(db_engine.sync_engine, "connect")
    def _postgres_timeouts(dbapi_connection, _connection_record) -> None:
        settings = get_settings()
        if settings.is_sqlite:
            return
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SET statement_timeout = '60s'")
            cursor.execute("SET lock_timeout = '10s'")
        finally:
            cursor.close()

    @event.listens_for(db_engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        settings = get_settings()
        if not settings.is_sqlite:
            return
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


settings = get_settings()
_pooler_configured = False

if settings.database_url.startswith("postgresql"):
    from db.supabase_url import log_database_target

    log_database_target(settings.database_url)

engine = create_async_engine(
    settings.database_url,
    **_engine_kwargs_for_url(settings.database_url),
)
_register_engine_events(engine)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def reconfigure_engine(database_url: str) -> None:
    """Пересоздать engine после успешного pooler probe."""
    global engine, async_session_factory

    old_engine = engine
    engine = create_async_engine(database_url, **_engine_kwargs_for_url(database_url))
    _register_engine_events(engine)
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    await old_engine.dispose()


async def configure_supabase_pooler() -> None:
    """На старте подобрать рабочий Supabase pooler (aws-0/aws-1, :5432/:6543)."""
    import os

    global _pooler_configured

    if _pooler_configured:
        return

    url = settings.database_url
    if "pooler.supabase.com" not in url:
        _pooler_configured = True
        return
    if os.environ.get("SUPABASE_POOLER_HOST", "").strip():
        _pooler_configured = True
        return

    from db.pooler_probe import probe_working_database_url

    working = await probe_working_database_url(url)
    if working != url:
        await reconfigure_engine(working)
        from db.supabase_url import log_database_target

        log_database_target(working)
    _pooler_configured = True


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session

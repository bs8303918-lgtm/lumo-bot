from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from config import get_settings


class Base(DeclarativeBase):
    pass


def _postgres_connect_args(database_url: str) -> dict:
    """asyncpg SSL + Supabase pooler quirks."""
    args: dict = {}
    if "pooler.supabase.com" in database_url or ":6543" in database_url:
        args["ssl"] = True
        args["statement_cache_size"] = 0
        args["prepared_statement_cache_size"] = 0
    elif "railway.internal" in database_url:
        pass
    else:
        args["ssl"] = True
    return args


settings = get_settings()

engine_kwargs: dict = {
    "echo": False,
    "pool_pre_ping": True,
}

if settings.is_sqlite:
    engine_kwargs["connect_args"] = {"timeout": 30}
    engine_kwargs["poolclass"] = NullPool
elif settings.database_url.startswith("postgresql"):
    engine_kwargs["connect_args"] = _postgres_connect_args(settings.database_url)
    if ":6543" in settings.database_url or "pooler.supabase.com" in settings.database_url:
        engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.database_url, **engine_kwargs)


@event.listens_for(engine.sync_engine, "connect")
def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    if not settings.is_sqlite:
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session

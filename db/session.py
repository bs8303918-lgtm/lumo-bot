"""Shared DB session helper — serializes SQLite writes to avoid 'database is locked'."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.base import async_session_factory

_SQLITE_WRITE_LOCK = asyncio.Lock()


@asynccontextmanager
async def open_db_session() -> AsyncIterator[AsyncSession]:
    """
    Open a DB session. For SQLite, only one writer at a time (WAL + asyncio lock).
    Use this instead of bare async_session_factory() in hot paths.
    """
    settings = get_settings()
    if settings.is_sqlite:
        async with _SQLITE_WRITE_LOCK:
            async with async_session_factory() as session:
                yield session
    else:
        async with async_session_factory() as session:
            yield session

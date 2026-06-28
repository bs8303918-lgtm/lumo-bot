"""Убрать kwargs, которые SQLAlchemy шлёт в asyncpg.connect, но asyncpg не понимает."""

from __future__ import annotations

import inspect
import logging

logger = logging.getLogger(__name__)

_PATCHED = False

_SA_ONLY = frozenset(
    {
        "async_fallback",
        "async_creator_fn",
        "prepared_statement_cache_size",
        "prepared_statement_name_func",
    }
)


def patch_sqlalchemy_asyncpg_connect() -> None:
    global _PATCHED
    if _PATCHED:
        return

    import asyncpg
    from sqlalchemy.dialects.postgresql import asyncpg as sa_asyncpg

    allowed = set(inspect.signature(asyncpg.connect).parameters)
    dbapi_cls = sa_asyncpg.AsyncAdapt_asyncpg_dbapi
    original = dbapi_cls.connect

    def connect(self, *arg, **kw):
        stripped: list[str] = []
        for key in list(kw):
            if key in allowed or key in _SA_ONLY:
                continue
            kw.pop(key, None)
            stripped.append(key)
        if stripped:
            logger.info(
                "asyncpg connect: stripped %s (asyncpg %s)",
                stripped,
                asyncpg.__version__,
            )
        return original(self, *arg, **kw)

    dbapi_cls.connect = connect  # type: ignore[method-assign]
    _PATCHED = True
    logger.info("SQLAlchemy/asyncpg compat patch enabled (asyncpg %s)", asyncpg.__version__)

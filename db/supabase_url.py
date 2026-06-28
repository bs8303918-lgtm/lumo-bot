"""Нормализация Supabase DATABASE_URL — pooler часто ломается на Railway."""

from __future__ import annotations

import logging
import os
import re
from urllib.parse import quote, unquote, urlparse

logger = logging.getLogger(__name__)

_PROJECT_REF_RE = re.compile(r"^postgres\.([a-z0-9]{10,30})$", re.I)


def _on_railway() -> bool:
    return bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))


def _use_direct_preferred() -> bool:
    raw = os.environ.get("SUPABASE_USE_DIRECT", "").strip().lower()
    if raw in ("0", "false", "no", "pooler"):
        return False
    if raw in ("1", "true", "yes", "direct"):
        return True
    return _on_railway()


def normalize_supabase_database_url(url: str) -> str:
    """
    Transaction pooler (6543) + SQLAlchemy/asyncpg → pgbouncer/tenant errors.
    На Railway по умолчанию: direct db.PROJECT_REF.supabase.co:5432 (user postgres).
    DATABASE_URL в Variables менять не нужно — достаточно pooler-строки из Supabase.
    """
    if not url.startswith("postgresql"):
        return url

    raw = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    username = unquote(parsed.username or "")
    password = parsed.password
    if not password:
        return url

    if host.startswith("db.") and host.endswith(".supabase.co") and username == "postgres":
        return url

    if not _use_direct_preferred():
        return url

    ref: str | None = None
    m = _PROJECT_REF_RE.match(username)
    if m:
        ref = m.group(1)
    elif host.startswith("db.") and host.endswith(".supabase.co"):
        ref = host.removeprefix("db.").removesuffix(".supabase.co")

    if not ref:
        return url

    encoded_pw = quote(unquote(password), safe="")
    direct = f"postgresql+asyncpg://postgres:{encoded_pw}@db.{ref}.supabase.co:5432/postgres"
    if direct != url:
        logger.info(
            "Supabase DB: using direct connection db.%s.supabase.co (set SUPABASE_USE_DIRECT=pooler to keep pooler)",
            ref,
        )
    return direct

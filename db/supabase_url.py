"""Нормализация Supabase DATABASE_URL для Railway (IPv4 + pooler)."""

from __future__ import annotations

import logging
import os
import re
from urllib.parse import quote, unquote, urlparse, urlunparse

logger = logging.getLogger(__name__)

_PROJECT_REF_RE = re.compile(r"^postgres\.([a-z0-9]{10,30})$", re.I)
_DOC_EXAMPLE_REFS = frozenset({"odfbsoitpodwrdawsotr"})


def _use_direct_explicit() -> bool:
    return os.environ.get("SUPABASE_USE_DIRECT", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "direct",
    )


def _to_direct(url: str) -> str | None:
    raw = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(raw)
    username = unquote(parsed.username or "")
    password = parsed.password
    if not password:
        return None
    ref: str | None = None
    m = _PROJECT_REF_RE.match(username)
    if m:
        ref = m.group(1)
    elif (parsed.hostname or "").startswith("db."):
        ref = (parsed.hostname or "").removeprefix("db.").removesuffix(".supabase.co")
    if not ref:
        return None
    encoded_pw = quote(unquote(password), safe="")
    return f"postgresql+asyncpg://postgres:{encoded_pw}@db.{ref}.supabase.co:5432/postgres"


def _warn_doc_example_ref(url: str) -> None:
    raw = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    username = unquote(urlparse(raw).username or "")
    match = _PROJECT_REF_RE.match(username)
    if match and match.group(1) in _DOC_EXAMPLE_REFS:
        logger.error(
            "DATABASE_URL uses example project ref %s from docs — "
            "replace with your Supabase project (Connect → URI).",
            match.group(1),
        )


def _replace_host(url: str, new_host: str) -> str:
    raw = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(raw)
    port = parsed.port or 5432
    netloc = parsed.netloc.split("@", 1)
    if len(netloc) != 2:
        return url
    auth, _old = netloc
    rebuilt = urlunparse(
        (
            "postgresql",
            f"{auth}@{new_host}:{port}",
            parsed.path or "/postgres",
            "",
            "",
            "",
        )
    )
    return rebuilt.replace("postgresql://", "postgresql+asyncpg://", 1)


def normalize_supabase_database_url(url: str) -> str:
    """
    Railway (IPv4): НЕ direct db.*.supabase.co — часто Network unreachable.

    По умолчанию:
    - transaction pooler :6543 → session pooler :5432 (тот же хост из DATABASE_URL)
    - optional SUPABASE_POOLER_HOST=aws-0-xxx.pooler.supabase.com если хост в URL неверный
    - direct только при SUPABASE_USE_DIRECT=true
    """
    if not url.startswith("postgresql"):
        return url

    _warn_doc_example_ref(url)

    if _use_direct_explicit():
        direct = _to_direct(url)
        if direct:
            logger.info("Supabase DB: direct connection (SUPABASE_USE_DIRECT=true)")
            return direct

    if "pooler.supabase.com" in url and ":6543" in url:
        updated = url.replace(":6543", ":5432", 1)
        if updated != url:
            logger.info("Supabase DB: session pooler :5432 instead of transaction :6543")
            url = updated

    override_host = os.environ.get("SUPABASE_POOLER_HOST", "").strip()
    if override_host and "pooler.supabase.com" in url:
        url = _replace_host(url, override_host)
        logger.info("Supabase DB: pooler host override -> %s", override_host)

    return url


def log_database_target(url: str) -> None:
    if not url.startswith("postgresql"):
        return
    raw = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(raw)
    try:
        import asyncpg

        asyncpg_ver = asyncpg.__version__
    except Exception:
        asyncpg_ver = "unknown"
    logger.info(
        "DB target: host=%s port=%s user=%s asyncpg=%s",
        parsed.hostname,
        parsed.port,
        parsed.username,
        asyncpg_ver,
    )

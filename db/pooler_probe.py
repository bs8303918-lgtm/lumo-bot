"""Проверка Supabase pooler: aws-0 vs aws-1 и session :5432 vs transaction :6543."""

from __future__ import annotations

import logging
import re
from urllib.parse import unquote, urlparse

logger = logging.getLogger(__name__)

_TENANT_RE = re.compile(r"tenant|user not found", re.I)
_AWS_POOLER_RE = re.compile(r"^aws-(\d+)-(.+\.pooler\.supabase\.com)$", re.I)
_PROJECT_REF_RE = re.compile(r"^postgres\.([a-z0-9]{10,30})$", re.I)

# Если регион в DATABASE_URL неверный — пробуем частые pooler Supabase.
_POOLER_REGION_SUFFIXES = (
    "ap-south-1.pooler.supabase.com",
    "ap-southeast-1.pooler.supabase.com",
    "eu-central-1.pooler.supabase.com",
    "eu-west-1.pooler.supabase.com",
    "us-east-1.pooler.supabase.com",
    "us-west-1.pooler.supabase.com",
)


def extract_project_ref(url: str) -> str | None:
    raw = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    username = unquote(urlparse(raw).username or "")
    match = _PROJECT_REF_RE.match(username)
    return match.group(1) if match else None


def is_tenant_not_found_error(exc: BaseException) -> bool:
    return bool(_TENANT_RE.search(str(exc)))


def pooler_host_variants(hostname: str | None) -> list[str]:
    if not hostname or "pooler.supabase.com" not in hostname:
        return [hostname] if hostname else []
    match = _AWS_POOLER_RE.match(hostname)
    if not match:
        return [hostname]
    idx, rest = match.group(1), match.group(2)
    alt = f"aws-{1 if idx == '0' else 0}-{rest}"
    hosts = [hostname]
    if alt not in hosts:
        hosts.append(alt)
    return hosts


def _set_port(url: str, port: int) -> str:
    from db.supabase_url import _replace_host

    raw = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(raw)
    host = parsed.hostname or ""
    return _replace_host(url, host).replace(f":{parsed.port or 5432}/", f":{port}/", 1)


def candidate_database_urls(url: str) -> list[str]:
    import os

    override = os.environ.get("SUPABASE_POOLER_HOST", "").strip()
    if override:
        base = _replace_host(url, override)
        return [_set_port(base, 5432), _set_port(base, 6543)]

    if "pooler.supabase.com" not in url:
        return [url]

    raw = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(raw)

    candidates: list[str] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        if candidate not in seen:
            seen.add(candidate)
            candidates.append(candidate)

    add(url)
    for host in pooler_host_variants(parsed.hostname):
        for port in (5432, 6543):
            add(_set_port(_replace_host(url, host), port))
    return candidates


def _region_sweep_candidates(url: str) -> list[str]:
    """Все aws-0/aws-1 × порты для типичных регионов pooler."""
    candidates: list[str] = []
    seen: set[str] = set()
    for suffix in _POOLER_REGION_SUFFIXES:
        for idx in (0, 1):
            host = f"aws-{idx}-{suffix}"
            for port in (5432, 6543):
                candidate = _set_port(_replace_host(url, host), port)
                if candidate not in seen:
                    seen.add(candidate)
                    candidates.append(candidate)
    return candidates


def _replace_host(url: str, new_host: str) -> str:
    from db.supabase_url import _replace_host as replace_host

    return replace_host(url, new_host)


async def _try_asyncpg_connect(url: str) -> None:
    import ssl

    raw = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(raw)
    port = parsed.port or 5432

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    connect_kwargs: dict = {
        "host": parsed.hostname,
        "port": port,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": (parsed.path or "/postgres").lstrip("/") or "postgres",
        "ssl": ctx,
        "timeout": 15,
    }
    if port == 6543:
        connect_kwargs["statement_cache_size"] = 0

    import asyncpg

    conn = await asyncpg.connect(**connect_kwargs)
    await conn.close()


async def probe_working_database_url(url: str) -> str:
    """Первый рабочий pooler URL или исходный, если не pooler / все попытки провалились."""
    if "pooler.supabase.com" not in url:
        return url

    last_error: Exception | None = None
    tenant_misses = 0
    tried: list[str] = []

    async def try_candidates(candidates: list[str], *, sweep: bool = False) -> str | None:
        nonlocal last_error, tenant_misses
        for candidate in candidates:
            parsed = urlparse(candidate.replace("postgresql+asyncpg://", "postgresql://", 1))
            label = f"{parsed.hostname}:{parsed.port}"
            if label in tried:
                continue
            tried.append(label)
            try:
                await _try_asyncpg_connect(candidate)
            except Exception as exc:
                last_error = exc
                if is_tenant_not_found_error(exc):
                    tenant_misses += 1
                    logger.warning("Supabase pooler probe tenant miss (%s)", label)
                    continue
                logger.warning("Supabase pooler probe failed (%s): %s", label, exc)
                continue
            if sweep:
                logger.info(
                    "Supabase pooler region sweep found %s — set SUPABASE_POOLER_HOST=%s in Railway",
                    label,
                    parsed.hostname,
                )
            elif candidate != url:
                logger.info("Supabase pooler probe selected %s", label)
            return candidate
        return None

    found = await try_candidates(candidate_database_urls(url))
    if found:
        return found

    import os

    if not os.environ.get("SUPABASE_POOLER_HOST", "").strip() and tenant_misses > 0:
        ref = extract_project_ref(url)
        logger.warning(
            "Supabase pooler: tenant miss on all local hosts (ref=%s), trying region sweep…",
            ref or "?",
        )
        sweep_list = _region_sweep_candidates(url)
        found = await try_candidates(sweep_list, sweep=True)
        if found:
            return found

    logger.error(
        "Supabase pooler probe: no host worked (last: %s). "
        "Supabase → Connect → URI → copy host → SUPABASE_POOLER_HOST on Railway.",
        last_error,
    )
    return url

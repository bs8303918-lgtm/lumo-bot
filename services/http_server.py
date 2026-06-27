"""HTTP API + Mini App static files — runs inside main.py."""

from __future__ import annotations

import logging

import uvicorn

from config import get_settings

logger = logging.getLogger(__name__)


async def run_api_server() -> None:
    settings = get_settings()
    if not settings.api_enabled:
        logger.info("API server disabled (API_ENABLED=false)")
        return

    config = uvicorn.Config(
        "api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    logger.info(
        "API + Mini App on http://%s:%s  (app: /app/  api: /api/)",
        settings.api_host,
        settings.api_port,
    )
    await server.serve()

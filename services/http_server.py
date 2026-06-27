"""HTTP API + Mini App static files — runs inside main.py."""

from __future__ import annotations

import logging

import uvicorn

from config import get_settings

logger = logging.getLogger(__name__)


async def run_api_server() -> None:
    import os

    settings = get_settings()
    if not settings.api_enabled:
        logger.info("API server disabled (API_ENABLED=false)")
        return

    port = int(os.environ.get("PORT", settings.api_port))

    config = uvicorn.Config(
        "api.app:app",
        host=settings.api_host,
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    logger.info(
        "API on http://%s:%s  (api: /api/%s)",
        settings.api_host,
        port,
        " mini-app: /app/" if settings.serve_mini_app else "",
    )
    await server.serve()

"""Local Telegram polling only — worker runs on Railway."""

import asyncio
import logging
import os

os.environ.setdefault("LUMO_MODE", "bot")

from main import main

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")

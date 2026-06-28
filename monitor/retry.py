import asyncio
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from logging_setup import log_error

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def run_with_retry(
    name: str,
    coro_factory: Callable[[], Any],
    max_retries: int = 5,
    base_delay: float = 5.0,
    on_critical: Callable[[Exception], Any] | None = None,
) -> None:
    attempt = 0
    while True:
        try:
            await coro_factory()
            attempt = 0
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            attempt += 1
            log_error(logger, name, exc, {"attempt": attempt})
            if on_critical and attempt >= max_retries:
                if attempt == max_retries:
                    await on_critical(exc)
            delay = min(base_delay * (2 ** (attempt - 1)), 300)
            logger.warning("%s failed (attempt %d), retry in %.1fs", name, attempt, delay)
            await asyncio.sleep(delay)

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import get_settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["traceback"] = "".join(traceback.format_exception(*record.exc_info))
        extra = getattr(record, "extra_data", None)
        if extra:
            payload["context"] = extra
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    settings = get_settings()
    settings.log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root.addHandler(console)

    app_file = logging.FileHandler(settings.log_dir / "app.log", encoding="utf-8")
    app_file.setFormatter(JsonFormatter())
    root.addHandler(app_file)

    error_file = logging.FileHandler(settings.log_dir / "errors.log", encoding="utf-8")
    error_file.setLevel(logging.ERROR)
    error_file.setFormatter(JsonFormatter())
    root.addHandler(error_file)


def log_error(
    logger: logging.Logger,
    module: str,
    error: Exception,
    context: dict[str, Any] | None = None,
) -> None:
    logger.error(
        "[%s] %s: %s",
        module,
        type(error).__name__,
        error,
        exc_info=True,
        extra={"extra_data": {"module": module, "error_type": type(error).__name__, **(context or {})}},
    )

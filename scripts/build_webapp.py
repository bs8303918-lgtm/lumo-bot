"""Build telegram-site frontend into dist/ for serving at /app/."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import BASE_DIR, WEBAPP_DIST_INDEX

logger = logging.getLogger(__name__)

FRONTEND_DIR = BASE_DIR / "telegram-site" / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
INDEX_FILE = WEBAPP_DIST_INDEX


def is_built() -> bool:
    return INDEX_FILE.is_file()


def _newest_source_mtime() -> float:
    newest = 0.0
    for path in (FRONTEND_DIR / "src", FRONTEND_DIR / "index.html", FRONTEND_DIR / "vite.config.js"):
        if not path.exists():
            continue
        if path.is_file():
            newest = max(newest, path.stat().st_mtime)
            continue
        for file in path.rglob("*"):
            if file.is_file():
                newest = max(newest, file.stat().st_mtime)
    return newest


def needs_rebuild() -> bool:
    if not is_built():
        return True
    return _newest_source_mtime() > INDEX_FILE.stat().st_mtime


def build_webapp(*, force: bool = False) -> bool:
    if is_built() and not force and not needs_rebuild():
        return True

    if not (FRONTEND_DIR / "package.json").is_file():
        logger.error("Mini App sources not found: %s", FRONTEND_DIR)
        return False

    npm = shutil.which("npm")
    if not npm:
        logger.error("npm not found — install Node.js to build Mini App")
        return False

    logger.info("Building Lumo Mini App...")
    env = {**os.environ, "VITE_BASE": "/app/"}

    if not (FRONTEND_DIR / "node_modules").is_dir():
        install = subprocess.run(
            [npm, "install"],
            cwd=FRONTEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
        if install.returncode != 0:
            logger.error("npm install failed:\n%s", install.stderr[-2000:])
            return False

    result = subprocess.run(
        [npm, "run", "build"],
        cwd=FRONTEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("npm run build failed:\n%s", result.stderr[-2000:])
        return False

    if is_built():
        logger.info("Mini App built → %s", DIST_DIR)
        return True

    logger.error("Build finished but %s missing", INDEX_FILE)
    return False


def ensure_webapp_built() -> None:
    if is_built() and not needs_rebuild():
        return
    if build_webapp():
        return
    logger.warning(
        "Mini App not built. Telegram Open button needs HTTPS URL + built app. "
        "Run: cd telegram-site\\frontend && npm install && npm run build"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ok = build_webapp(force="--force" in sys.argv)
    sys.exit(0 if ok else 1)

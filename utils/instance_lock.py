import logging
import os
import subprocess
import sys
from pathlib import Path

from config import BASE_DIR

logger = logging.getLogger(__name__)

LOCK_FILE = BASE_DIR / ".lumo.lock"


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def acquire_instance_lock() -> None:
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
        except ValueError:
            old_pid = 0
        if _pid_running(old_pid):
            raise SystemExit(
                f"Lumo already running (PID {old_pid}). "
                "Stop the other instance before starting again."
            )
        logger.warning("Removing stale Lumo lock (PID %s no longer running)", old_pid)
        LOCK_FILE.unlink(missing_ok=True)
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")


def release_instance_lock() -> None:
    try:
        if LOCK_FILE.exists() and LOCK_FILE.read_text(encoding="utf-8").strip() == str(os.getpid()):
            LOCK_FILE.unlink()
    except OSError:
        pass

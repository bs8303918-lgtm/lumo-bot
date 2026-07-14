"""Разослать объявление о платном режиме всем пользователям бота.

Usage:
  python scripts/send_paid_mode_notice.py dry
  python scripts/send_paid_mode_notice.py
  python scripts/send_paid_mode_notice.py force
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.paid_mode_broadcast import send_paid_mode_notice  # noqa: E402


async def main() -> None:
    args = {a.lower() for a in sys.argv[1:]}
    dry_run = "dry" in args
    force = "force" in args
    stats = await send_paid_mode_notice(force=force, dry_run=dry_run)
    label = "DRY-RUN" if dry_run else "DONE"
    print(
        f"[{label}] target={stats['target']} sent={stats['sent']} "
        f"skipped={stats['skipped']} unreachable={stats['unreachable']} "
        f"error={stats['error']}"
    )


if __name__ == "__main__":
    asyncio.run(main())

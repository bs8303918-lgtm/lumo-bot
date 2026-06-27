"""Разослать извинение за техобслуживание новым пользователям."""
from __future__ import annotations

import asyncio
import sys

from bot.instance import close_bot
from services.maintenance_broadcast import get_registered_user_ids, send_maintenance_apology


async def main() -> None:
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    welcome = "--welcome" in sys.argv
    days = 7
    for arg in sys.argv[1:]:
        if arg.isdigit():
            days = int(arg)

    ids = await get_registered_user_ids(days=days)
    print(f"Target users ({days}d): {len(ids)}")
    if dry_run:
        print("Dry-run only — add without --dry-run to send")
        return

    stats = await send_maintenance_apology(
        days=days,
        force=force,
        resend_welcome=welcome,
        dry_run=False,
    )
    print(stats)
    await close_bot()


if __name__ == "__main__":
    asyncio.run(main())

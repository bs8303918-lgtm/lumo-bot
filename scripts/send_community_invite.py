"""Разовая рассылка приглашения в сообщество Lumo."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.community_broadcast import send_community_invite


async def main() -> None:
    dry = "--dry" in sys.argv
    force = "--force" in sys.argv
    stats = await send_community_invite(force=force, dry_run=dry)
    print(
        f"target={stats['target']} sent={stats['sent']} "
        f"skipped={stats['skipped']} unreachable={stats['unreachable']} error={stats['error']}"
    )


if __name__ == "__main__":
    asyncio.run(main())

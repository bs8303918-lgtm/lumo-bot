"""CLI: экспорт training_samples в JSONL."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.training_export import export_training_jsonl


async def main() -> None:
    task = sys.argv[1] if len(sys.argv) > 1 else None
    path = await export_training_jsonl(task=task)
    lines = sum(1 for _ in path.open(encoding="utf-8"))
    print(f"Exported {lines} rows -> {path}")


if __name__ == "__main__":
    asyncio.run(main())

"""Экспорт training_samples в JSONL."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from config import get_settings
from db.base import async_session_factory
from db.repositories.training import TrainingRepository
from services.training_collector import sample_to_jsonl


async def export_training_jsonl(
    *,
    task: str | None = None,
    since: datetime | None = None,
    limit: int = 50_000,
    output_path: Path | None = None,
) -> Path:
    settings = get_settings()
    out_dir = settings.training_data_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        suffix = f"_{task}" if task else ""
        output_path = out_dir / f"lumo_training{suffix}_{stamp}.jsonl"

    async with async_session_factory() as session:
        repo = TrainingRepository(session)
        rows = await repo.iter_export_rows(task=task, since=since, limit=limit)

    with output_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(sample_to_jsonl(row))
            fh.write("\n")

    return output_path

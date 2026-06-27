import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import TrainingSample


class TrainingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        *,
        task: str,
        input_data: dict,
        output_data: dict,
        raw_message_id: int | None = None,
        catalog_id: int | None = None,
        user_id: int | None = None,
        source_channel: str | None = None,
        model_name: str | None = None,
        meta: dict | None = None,
    ) -> TrainingSample:
        row = TrainingSample(
            task=task,
            raw_message_id=raw_message_id,
            catalog_id=catalog_id,
            user_id=user_id,
            source_channel=source_channel,
            input_json=json.dumps(input_data, ensure_ascii=False),
            output_json=json.dumps(output_data, ensure_ascii=False),
            model_name=model_name,
            meta_json=json.dumps(meta, ensure_ascii=False) if meta else None,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def count_total(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(TrainingSample))
        return int(result.scalar_one())

    async def count_by_task(self) -> dict[str, int]:
        result = await self.session.execute(
            select(TrainingSample.task, func.count())
            .group_by(TrainingSample.task)
            .order_by(TrainingSample.task)
        )
        return {task: int(count) for task, count in result.all()}

    async def iter_export_rows(
        self,
        *,
        task: str | None = None,
        since: datetime | None = None,
        limit: int = 50_000,
    ) -> list[TrainingSample]:
        stmt = select(TrainingSample).order_by(TrainingSample.id)
        if task:
            stmt = stmt.where(TrainingSample.task == task)
        if since:
            stmt = stmt.where(TrainingSample.created_at >= since)
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

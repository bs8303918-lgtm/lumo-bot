"""Фоновый сбор данных для будущего обучения моделей Lumo."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from config import get_settings
from db.base import async_session_factory
from db.models import CatalogOpportunity, RawMessage
from db.repositories.training import TrainingRepository

logger = logging.getLogger(__name__)


def _channel_name(channel) -> str:
    if channel is None:
        return ""
    return channel.channel_title or channel.channel_identifier or ""


def _posted_at_iso(raw_message: RawMessage) -> str | None:
    if raw_message.posted_at is None:
        return None
    dt = raw_message.posted_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


async def _save(
    *,
    task: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    raw_message_id: int | None = None,
    catalog_id: int | None = None,
    user_id: int | None = None,
    source_channel: str | None = None,
    model_name: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    settings = get_settings()
    if not settings.training_data_enabled:
        return
    try:
        async with async_session_factory() as session:
            repo = TrainingRepository(session)
            await repo.add(
                task=task,
                input_data=input_data,
                output_data=output_data,
                raw_message_id=raw_message_id,
                catalog_id=catalog_id,
                user_id=user_id,
                source_channel=source_channel,
                model_name=model_name,
                meta=meta,
            )
            await session.commit()
    except Exception as exc:
        logger.debug("Training sample not saved (%s): %s", task, exc)


async def record_classify(
    raw_message: RawMessage,
    channel,
    *,
    llm_output: dict[str, Any] | None,
    final_output: dict[str, Any],
    source: str,
    model_name: str | None = None,
    catalog_id: int | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> None:
    """Классификация поста: spam-фильтр, LLM или пост-валидация."""
    meta = {"source": source, "collected_at": datetime.now(timezone.utc).isoformat()}
    if extra_meta:
        meta.update(extra_meta)
    await _save(
        task="classify",
        input_data={
            "message": raw_message.text,
            "channel": _channel_name(channel),
            "message_link": raw_message.message_link,
            "posted_at": _posted_at_iso(raw_message),
        },
        output_data={
            "llm": llm_output,
            "final": final_output,
        },
        raw_message_id=raw_message.id,
        catalog_id=catalog_id,
        source_channel=_channel_name(channel),
        model_name=model_name,
        meta=meta,
    )


async def record_match(
    *,
    user_id: int,
    interest_query: str,
    entry: CatalogOpportunity | dict[str, Any],
    relevant: bool,
    score: float | None = None,
    source: str = "catalog",
    raw_message_id: int | None = None,
    catalog_id: int | None = None,
    categories: list[str] | None = None,
) -> None:
    """Решение о релевантности поста для пользователя (локальный скоринг или отправка)."""
    if isinstance(entry, CatalogOpportunity):
        opportunity = {
            "title": entry.title,
            "type": entry.opportunity_type,
            "deadline": entry.deadline,
            "description": entry.description,
            "requirements": entry.requirements,
            "source_channel_name": entry.source_channel_name,
            "message_link": entry.message_link,
        }
        raw_message_id = raw_message_id or entry.raw_message_id
        catalog_id = catalog_id or entry.id
    else:
        opportunity = entry

    await _save(
        task="match",
        input_data={
            "interest_query": interest_query,
            "categories": categories or [],
            "opportunity": opportunity,
        },
        output_data={
            "relevant": relevant,
            "score": score,
            "sent": relevant,
        },
        raw_message_id=raw_message_id,
        catalog_id=catalog_id,
        user_id=user_id,
        source_channel=opportunity.get("source_channel_name"),
        meta={"source": source, "collected_at": datetime.now(timezone.utc).isoformat()},
    )


async def record_relevance_llm(
    *,
    user_id: int,
    interest_query: str,
    raw_message: RawMessage,
    channel,
    llm_output: dict[str, Any],
    relevant: bool,
    model_name: str | None = None,
) -> None:
    """LLM check_relevance (если включён pair relevance)."""
    await _save(
        task="relevance",
        input_data={
            "interest_query": interest_query,
            "message": raw_message.text,
            "channel": _channel_name(channel),
            "message_link": raw_message.message_link,
        },
        output_data={
            "llm": llm_output,
            "relevant": relevant,
        },
        raw_message_id=raw_message.id,
        user_id=user_id,
        source_channel=_channel_name(channel),
        model_name=model_name,
        meta={"source": "llm_pair", "collected_at": datetime.now(timezone.utc).isoformat()},
    )


async def record_interest_categories(
    *,
    user_id: int,
    interest_query: str,
    categories: list[str],
    source: str = "local",
) -> None:
    """Извлечение категорий из профиля пользователя."""
    await _save(
        task="categories",
        input_data={"interest_query": interest_query},
        output_data={"categories": categories},
        user_id=user_id,
        meta={"source": source, "collected_at": datetime.now(timezone.utc).isoformat()},
    )


async def record_search_feedback(
    *,
    user_id: int,
    interest_query: str,
    catalog_id: int,
    helpful: bool,
    categories: list[str] | None = None,
) -> None:
    """Оценка пользователя: карточка совпала с запросом или нет (для обучения match)."""
    from db.repositories.opportunity_catalog import OpportunityCatalogRepository

    async with async_session_factory() as session:
        repo = OpportunityCatalogRepository(session)
        row = await repo.get_entry_with_channel(catalog_id)
        if not row:
            return
        entry, _channel = row

    await record_match(
        user_id=user_id,
        interest_query=interest_query,
        entry=entry,
        relevant=helpful,
        score=None,
        source="user_feedback",
        catalog_id=catalog_id,
        categories=categories,
    )


def sample_to_jsonl(row) -> str:
    """Одна строка JSONL в формате, удобном для fine-tuning."""
    input_data = json.loads(row.input_json)
    output_data = json.loads(row.output_json)
    meta = json.loads(row.meta_json) if row.meta_json else {}
    payload = {
        "id": row.id,
        "task": row.task,
        "input": input_data,
        "output": output_data,
        "model": row.model_name,
        "meta": meta,
        "raw_message_id": row.raw_message_id,
        "catalog_id": row.catalog_id,
        "user_id": row.user_id,
        "source_channel": row.source_channel,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
    return json.dumps(payload, ensure_ascii=False)

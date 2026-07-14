"""LLM rerank over keyword-filtered catalog candidates (lightweight RAG)."""

from __future__ import annotations

import logging

from config import get_settings
from db.models import CatalogOpportunity
from llm.client import LLMClient

logger = logging.getLogger(__name__)


def _serialize_for_llm(entry: CatalogOpportunity) -> dict:
    return {
        "id": entry.id,
        "type": entry.opportunity_type,
        "title": entry.title or "",
        "description": (entry.description or "")[:200],
    }


async def llm_rerank_catalog(
    interest_query: str,
    candidates: list[CatalogOpportunity],
    *,
    max_pick: int,
    pool_size: int = 25,
) -> list[CatalogOpportunity]:
    settings = get_settings()
    if not settings.llm_catalog_match_rerank or not settings.llm_configured:
        return candidates[:max_pick]
    if not candidates:
        return []

    pool = candidates[:pool_size]
    try:
        picked_ids, _raw = await LLMClient().match_catalog_items(
            interest_query,
            [_serialize_for_llm(entry) for entry in pool],
            max_pick=max_pick,
        )
        if not picked_ids:
            return candidates[:max_pick]

        by_id = {entry.id: entry for entry in pool}
        reranked = [by_id[item_id] for item_id in picked_ids if item_id in by_id]
        seen = {entry.id for entry in reranked}
        for entry in candidates:
            if entry.id not in seen and len(reranked) < max_pick:
                reranked.append(entry)
        return reranked
    except Exception as exc:
        logger.warning("LLM catalog rerank failed: %s", exc)
        return candidates[:max_pick]

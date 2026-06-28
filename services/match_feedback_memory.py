"""Живая память 👍/👎 — сразу влияет на локальный матчинг, плюс копится в training."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field

from sqlalchemy import select

from db.base import async_session_factory
from db.models import TrainingSample

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 300.0
_user_cache: dict[int, tuple[float, "FeedbackHints"]] = {}
_optimistic: dict[int, dict[int, tuple[bool, str]]] = {}


def record_optimistic_feedback(
    user_id: int,
    catalog_id: int,
    helpful: bool,
    query: str,
) -> None:
    """Сразу после 👍/👎 в UI — до записи в БД."""
    bucket = _optimistic.setdefault(user_id, {})
    bucket[catalog_id] = (helpful, query.strip())
    _user_cache.pop(user_id, None)


def _merge_optimistic(user_id: int, hints: FeedbackHints) -> FeedbackHints:
    pending = _optimistic.get(user_id)
    if not pending:
        return hints
    neg_queries = list(hints._user_negative_queries)
    negatives = set(hints.user_negative_ids)
    positives = set(hints.user_positive_ids)
    for cid, (helpful, query) in pending.items():
        if helpful:
            positives.add(cid)
            negatives.discard(cid)
        else:
            negatives.add(cid)
            positives.discard(cid)
            neg_queries.append((cid, query))
    return FeedbackHints(
        user_negative_ids=negatives,
        user_positive_ids=positives,
        global_negative_ids=set(hints.global_negative_ids),
        _user_negative_queries=neg_queries,
    )


def _normalize_query(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().strip())[:500]


def queries_similar(a: str, b: str) -> bool:
    na, nb = _normalize_query(a), _normalize_query(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if na in nb or nb in na:
        return True
    ta = {t for t in re.findall(r"[\w]{4,}", na, flags=re.UNICODE)}
    tb = {t for t in re.findall(r"[\w]{4,}", nb, flags=re.UNICODE)}
    if not ta or not tb:
        return False
    overlap = len(ta & tb) / min(len(ta), len(tb))
    return overlap >= 0.45


@dataclass
class FeedbackHints:
    user_negative_ids: set[int] = field(default_factory=set)
    user_positive_ids: set[int] = field(default_factory=set)
    query_negative_ids: set[int] = field(default_factory=set)
    global_negative_ids: set[int] = field(default_factory=set)
    _user_negative_queries: list[tuple[int, str]] = field(default_factory=list, repr=False)

    def attach_query_negatives(self, interest_query: str) -> "FeedbackHints":
        if not self._user_negative_queries:
            return self
        qneg = {
            cid
            for cid, q in self._user_negative_queries
            if queries_similar(interest_query, q)
        }
        if not qneg:
            return self
        merged = FeedbackHints(
            user_negative_ids=set(self.user_negative_ids),
            user_positive_ids=set(self.user_positive_ids),
            query_negative_ids=qneg,
            global_negative_ids=set(self.global_negative_ids),
        )
        return merged


def invalidate_feedback_cache(user_id: int | None = None) -> None:
    if user_id is None:
        _user_cache.clear()
    else:
        _user_cache.pop(user_id, None)


def apply_feedback_score(
    base_score: float,
    catalog_id: int,
    hints: FeedbackHints | None,
) -> float | None:
    """None = полностью скрыть карточку для этого пользователя."""
    if hints is None:
        return base_score
    if (
        catalog_id in hints.user_negative_ids
        or catalog_id in hints.query_negative_ids
    ):
        return None
    score = base_score
    if catalog_id in hints.global_negative_ids:
        score *= 0.2
    if catalog_id in hints.user_positive_ids:
        score += 4.0
    return score


async def load_match_feedback_hints(
    user_id: int | None,
    interest_query: str,
    *,
    max_rows: int = 120,
) -> FeedbackHints:
    if user_id is None:
        return FeedbackHints()

    now = time.monotonic()
    cached = _user_cache.get(user_id)
    if cached and now - cached[0] < _CACHE_TTL_SEC:
        merged = _merge_optimistic(user_id, cached[1])
        return merged.attach_query_negatives(interest_query)

    hints = FeedbackHints()
    user_latest: dict[int, bool] = {}
    global_neg_counts: dict[int, int] = {}
    negative_queries: list[tuple[int, str]] = []

    try:
        async with async_session_factory() as session:
            user_result = await session.execute(
                select(TrainingSample)
                .where(TrainingSample.task == "match")
                .where(TrainingSample.user_id == user_id)
                .where(TrainingSample.catalog_id.isnot(None))
                .order_by(TrainingSample.id.desc())
                .limit(max_rows)
            )
            user_rows = list(user_result.scalars().all())

            global_result = await session.execute(
                select(TrainingSample.catalog_id, TrainingSample.output_json)
                .where(TrainingSample.task == "match")
                .where(TrainingSample.catalog_id.isnot(None))
                .order_by(TrainingSample.id.desc())
                .limit(max_rows)
            )
            global_rows = list(global_result.all())
    except Exception as exc:
        logger.debug("load_match_feedback_hints failed: %s", exc)
        return hints

    for row in user_rows:
        if row.catalog_id is None:
            continue
        cid = int(row.catalog_id)
        if cid in user_latest:
            continue
        try:
            output = json.loads(row.output_json or "{}")
        except json.JSONDecodeError:
            continue
        relevant = bool(output.get("relevant"))
        user_latest[cid] = relevant
        if not relevant:
            try:
                inp = json.loads(row.input_json or "{}")
            except json.JSONDecodeError:
                inp = {}
            negative_queries.append((cid, str(inp.get("interest_query") or "")))

    for catalog_id, output_json in global_rows:
        if catalog_id is None:
            continue
        try:
            output = json.loads(output_json or "{}")
        except json.JSONDecodeError:
            continue
        if not bool(output.get("relevant")):
            cid = int(catalog_id)
            global_neg_counts[cid] = global_neg_counts.get(cid, 0) + 1

    hints.user_negative_ids = {cid for cid, ok in user_latest.items() if not ok}
    hints.user_positive_ids = {cid for cid, ok in user_latest.items() if ok}
    hints._user_negative_queries = negative_queries
    hints.global_negative_ids = {cid for cid, n in global_neg_counts.items() if n >= 2}

    hints = _merge_optimistic(user_id, hints)
    resolved = hints.attach_query_negatives(interest_query)
    _user_cache[user_id] = (now, hints)
    return resolved

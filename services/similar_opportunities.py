"""«Похожие конкурсы» — контентная схожесть по тегам/типу/стране, без эмбеддингов."""

from __future__ import annotations

from db.models import CatalogOpportunity
from services.catalog_country import normalize_country
from services.interest_matcher import entry_all_tags


def _tag_set(entry: CatalogOpportunity) -> set[str]:
    tags = {t.lower().strip() for t in entry_all_tags(entry)}
    tags.add((entry.opportunity_type or "").lower().strip())
    tags.discard("")
    return tags


def similarity_score(base: CatalogOpportunity, candidate: CatalogOpportunity) -> float:
    base_tags = _tag_set(base)
    candidate_tags = _tag_set(candidate)
    if not base_tags or not candidate_tags:
        return 0.0

    intersection = base_tags & candidate_tags
    union = base_tags | candidate_tags
    jaccard = len(intersection) / len(union) if union else 0.0

    score = jaccard * 10.0
    if base.opportunity_type == candidate.opportunity_type:
        score += 2.0
    if normalize_country(getattr(base, "country", None)) == normalize_country(getattr(candidate, "country", None)):
        score += 1.0
    return score


def find_similar(
    base: CatalogOpportunity,
    pool: list[CatalogOpportunity],
    *,
    limit: int = 6,
    min_score: float = 2.0,
) -> list[CatalogOpportunity]:
    scored = [
        (similarity_score(base, candidate), candidate)
        for candidate in pool
        if candidate.id != base.id
    ]
    scored = [(score, entry) for score, entry in scored if score >= min_score]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [entry for _, entry in scored[:limit]]

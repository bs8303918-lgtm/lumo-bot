"""Tests for specialty-aware interest matching."""

from __future__ import annotations

from dataclasses import dataclass, field

from services.interest_categorizer import _needs_llm_categorization
from services.interest_matcher import relevance_score, resolve_catalog_filter
from services.interest_profile import (
    InterestProfile,
    apply_interest_defaults,
    infer_types_from_domains,
    parse_interest_profile,
)


@dataclass
class FakeEntry:
    title: str = ""
    description: str = ""
    requirements: str | None = None
    opportunity_type: str = "конкурс"
    tags_json: str | None = None

    def __post_init__(self) -> None:
        if self.tags_json is None:
            import json

            self.tags_json = json.dumps([self.opportunity_type], ensure_ascii=False)


def test_infer_types_from_biology_domains():
    assert "олимпиада" in infer_types_from_domains(["биология"])
    assert "стипендия" in infer_types_from_domains(["биология"])


def test_apply_defaults_use_domain_not_only_contest():
    profile = InterestProfile(types=[], domains=["биология"])
    apply_interest_defaults(profile, "Школьница, люблю биологию")
    assert "олимпиада" in profile.types
    assert profile.types != ["конкурс"]


def test_resolve_catalog_filter_narrows_by_domain():
    types, extra = resolve_catalog_filter(["биология"])
    assert "олимпиада" in types
    assert extra == ["биология"]


def test_relevance_penalizes_unrelated_startup_for_biology():
    biology_text = "Школьница 10 класс, люблю биологию — ищу олимпиады и стипендии"
    bio_entry = FakeEntry(
        title="Олимпиада по биологии",
        description="для школьников Казахстана",
        opportunity_type="олимпиада",
        tags_json='["олимпиада", "биология"]',
    )
    startup_entry = FakeEntry(
        title="Startup pitch battle",
        description="питчинг для стартапов Astana Hub",
        opportunity_type="хакатон",
        tags_json='["хакатон", "стартапы"]',
    )
    bio_score = relevance_score(biology_text, bio_entry)
    startup_score = relevance_score(biology_text, startup_entry)
    assert bio_score > startup_score


def test_parse_profile_keeps_specialty_domains():
    profile = parse_interest_profile("Студентка, увлекаюсь астрофизикой, ищу стипендии")
    assert "астрофизика" in profile.domains or "астрофизика" in profile.all_categories()


def test_needs_llm_for_vague_or_unrecognized_interests():
    vague = parse_interest_profile("что-то интересное, посоветуй", apply_defaults=False)
    assert _needs_llm_categorization(vague, "что-то интересное, посоветуй") is True

    unrecognized = parse_interest_profile("примерно про IT и биологию", apply_defaults=False)
    assert _needs_llm_categorization(unrecognized, "примерно про IT и биологию") is True

"""Unit tests for benchmark matching comparison."""

from benchmark.compare import (
    compare_matching,
    deadlines_match,
    list_overlap_score,
    normalize_prediction,
    summarize_model_agreement,
    text_similarity,
)
from benchmark.schema import CompareResult, MatchingGolden


def test_deadlines_match_iso():
    assert deadlines_match("2026-10-15", "2026-10-15") is True


def test_false_negative_detected():
    golden = MatchingGolden(
        is_opportunity=True,
        category="олимпиада",
        matches_profile=True,
        is_eligible=True,
    )
    result = compare_matching(
        record_id="t1",
        model="test",
        golden=golden,
        predicted={"is_opportunity": False, "category": "не_возможность"},
    )
    assert any(e.category == "false_negative" for e in result.errors)


def test_eligibility_mismatch():
    golden = MatchingGolden(is_opportunity=True, is_eligible=True, matches_profile=True)
    result = compare_matching(
        record_id="t2",
        model="test",
        golden=golden,
        predicted={
            "is_opportunity": True,
            "is_eligible": False,
            "matches_profile": True,
        },
    )
    assert any(e.field == "is_eligible" for e in result.errors)


def test_normalize_prediction():
    data = normalize_prediction(
        {
            "category": "Hackathon",
            "key_benefits": ["grant"],
            "matched_skills": ["Python"],
        }
    )
    assert data["category"] == "хакатон"
    assert data["key_benefits"] == ["grant"]


def test_model_agreement():
    results = [
        CompareResult(
            record_id="p1",
            model="a",
            predicted={"is_eligible": True, "category": "хакатон"},
        ),
        CompareResult(
            record_id="p1",
            model="b",
            predicted={"is_eligible": True, "category": "хакатон"},
        ),
        CompareResult(
            record_id="p1",
            model="c",
            predicted={"is_eligible": False, "category": "хакатон"},
        ),
    ]
    agreement = summarize_model_agreement(results)
    assert agreement["posts_with_multiple_models"] == 1
    assert agreement["field_agreement"]["is_eligible"]["split"] == 1


def test_list_overlap():
    assert list_overlap_score(["Python", "стартапы"], ["python", "AI"]) >= 0.4


def test_text_similarity():
    assert text_similarity("DAAD scholarship", "DAAD scholarship for masters") >= 0.5

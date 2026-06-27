"""Tests for multi-item classification expansion."""

from llm.classification_utils import expand_classification_items


def test_expand_single_legacy_object():
    data = {
        "is_opportunity": True,
        "title": "AI Hackathon",
        "type": "хакатон",
        "deadline": "01.07.2026",
        "description": "One event",
    }
    items = expand_classification_items(data)
    assert len(items) == 1
    assert items[0]["title"] == "AI Hackathon"


def test_expand_roundup_into_many():
    data = {
        "is_opportunity": True,
        "opportunities": [
            {
                "title": "Seoul National University - SNU Global Scholarship",
                "type": "стипендия",
                "deadline": "не указан",
                "description": "Tuition + housing",
            },
            {
                "title": "Korea University - Global Leader Scholarship A",
                "type": "грант",
                "deadline": "не указан",
                "description": "Full tuition",
            },
        ],
    }
    items = expand_classification_items(data)
    assert len(items) == 2
    assert "Seoul National University" in items[0]["title"]
    assert "Korea University" in items[1]["title"]


def test_not_opportunity_returns_one_stub():
    items = expand_classification_items({"is_opportunity": False})
    assert len(items) == 1
    assert items[0]["is_opportunity"] is False

from datetime import datetime, timedelta, timezone

from db.models import CatalogOpportunity
from services.catalog_display import (
    entry_has_cash_prize,
    format_deadline_label,
    is_entry_new,
    sort_opportunities_by_newest,
)


def _entry(**kwargs) -> CatalogOpportunity:
    defaults = {
        "id": 1,
        "opportunity_type": "конкурс",
        "title": "Test",
        "description": "",
        "requirements": None,
        "deadline": "не указан",
        "is_active": True,
        "classified_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return CatalogOpportunity(**defaults)


def test_startup_battle_has_cash_prize():
    entry = _entry(
        title="STARTUP BATTLE на 500к₸ от LaunchZone",
        description="Денежный приз для школьников",
    )
    assert entry_has_cash_prize(entry) is True


def test_no_cash_prize():
    entry = _entry(title="Лекция про карьеру", description="Бесплатное мероприятие")
    assert entry_has_cash_prize(entry) is False


def test_is_entry_new():
    entry = _entry(classified_at=datetime.now(timezone.utc))
    assert is_entry_new(entry) is True


def test_is_entry_old():
    entry = _entry(classified_at=datetime.now(timezone.utc) - timedelta(days=10))
    assert is_entry_new(entry) is False


def test_sort_newest_first():
    older = _entry(id=1, classified_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    newer = _entry(id=2, classified_at=datetime(2026, 7, 1, tzinfo=timezone.utc))
    sorted_items = sort_opportunities_by_newest([older, newer])
    assert [item.id for item in sorted_items] == [2, 1]


def test_format_deadline_label_unknown():
    meta = format_deadline_label("не указан")
    assert meta["label"] == "не указан"
    assert meta["urgent"] is False

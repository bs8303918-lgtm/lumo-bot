"""Tests for Startify trial grant on /start."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from db.models import User
from services.subscription import PLAN_TRIAL_7D
from services.subscription_trial import apply_startify_start


def _user(**kwargs) -> User:
    u = User(id=1, telegram_id=111, username="t")
    u.tariff_plan = kwargs.get("tariff_plan", "freemium")
    u.tariff_expires_at = kwargs.get("tariff_expires_at")
    return u


@pytest.mark.asyncio
async def test_startify_link_grants_trial_once():
    session = AsyncMock()
    state: dict[str, str] = {}

    state_repo = MagicMock()
    state_repo.get = AsyncMock(side_effect=lambda k, d="0": state.get(k, d))
    state_repo.set = AsyncMock(side_effect=lambda k, v: state.update({k: v}))

    event_repo = MagicMock()
    event_repo.log = AsyncMock()
    session.flush = AsyncMock()

    import services.subscription_trial as mod

    orig_state = mod.SystemStateRepository
    orig_event = mod.EventRepository
    mod.SystemStateRepository = lambda s: state_repo
    mod.EventRepository = lambda s: event_repo
    try:
        user = _user()
        result = await apply_startify_start(session, user, "sf_ref_grants")
    finally:
        mod.SystemStateRepository = orig_state
        mod.EventRepository = orig_event

    assert result.attributed is True
    assert result.trial_granted is True
    assert user.tariff_plan == PLAN_TRIAL_7D
    assert user.partner_ref == "grants"


@pytest.mark.asyncio
async def test_paid_plan_in_link_skips_trial():
    session = AsyncMock()
    state_repo = MagicMock()
    state_repo.get = AsyncMock(return_value="0")
    state_repo.set = AsyncMock()
    event_repo = MagicMock()
    event_repo.log = AsyncMock()
    session.flush = AsyncMock()

    import services.subscription_trial as mod

    orig_state = mod.SystemStateRepository
    orig_event = mod.EventRepository
    mod.SystemStateRepository = lambda s: state_repo
    mod.EventRepository = lambda s: event_repo
    try:
        user = _user()
        result = await apply_startify_start(session, user, "sf_ref_pricing_plan_6m")
    finally:
        mod.SystemStateRepository = orig_state
        mod.EventRepository = orig_event

    assert result.attributed is True
    assert result.trial_granted is False


@pytest.mark.asyncio
async def test_trial_not_regranted_after_used():
    session = AsyncMock()
    state = {"startify_trial_used:1": "1"}
    state_repo = MagicMock()
    state_repo.get = AsyncMock(side_effect=lambda k, d="0": state.get(k, d))
    state_repo.set = AsyncMock()
    event_repo = MagicMock()
    event_repo.log = AsyncMock()
    session.flush = AsyncMock()

    import services.subscription_trial as mod

    orig_state = mod.SystemStateRepository
    orig_event = mod.EventRepository
    mod.SystemStateRepository = lambda s: state_repo
    mod.EventRepository = lambda s: event_repo
    try:
        user = _user(
            tariff_plan=PLAN_TRIAL_7D,
            tariff_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        result = await apply_startify_start(session, user, "sf_ref_grants")
    finally:
        mod.SystemStateRepository = orig_state
        mod.EventRepository = orig_event

    assert result.trial_granted is False

"""Tests for match digest batching."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.match_digest import MatchDigestBuffer, PendingMatch


@pytest.mark.asyncio
async def test_flush_remaining_caps_items():
    buffer = MatchDigestBuffer(batch_size=5)
    ns = MagicMock()
    ns.send_digest = AsyncMock(return_value=True)

    for i in range(5):
        buffer.add(1, 100, i, {"title": f"Card {i}"})

    sent = await buffer.flush_remaining(1, ns, max_items=3)

    assert sent == 3
    assert buffer.pending_count(1) == 2
    ns.send_digest.assert_called_once()
    batch = ns.send_digest.call_args[0][1]
    assert len(batch) == 3


@pytest.mark.asyncio
async def test_flush_ready_sends_full_batch_only():
    buffer = MatchDigestBuffer(batch_size=3)
    ns = MagicMock()
    ns.send_digest = AsyncMock(return_value=True)

    for i in range(2):
        buffer.add(1, 100, i, {"title": f"Card {i}"})

    sent = await buffer.flush_ready(1, ns)
    assert sent == 0
    assert buffer.pending_count(1) == 2

    buffer.add(1, 100, 2, {"title": "Card 2"})
    sent = await buffer.flush_ready(1, ns)
    assert sent == 3
    assert buffer.pending_count(1) == 0

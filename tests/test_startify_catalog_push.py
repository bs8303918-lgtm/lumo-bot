"""Tests for Startify catalog push webhook."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import startify_catalog_push as mod


def test_is_push_configured_requires_url_and_key():
    settings = MagicMock(
        startify_catalog_push_enabled=True,
        startify_catalog_webhook_url="https://api.startify.example/hook",
        partner_api_key="secret",
    )
    with patch.object(mod, "get_settings", return_value=settings):
        assert mod.is_push_configured() is True

    settings.partner_api_key = ""
    with patch.object(mod, "get_settings", return_value=settings):
        assert mod.is_push_configured() is False


def test_build_webhook_payload_shape():
    payload = mod.build_webhook_payload(
        mod.EVENT_CREATED,
        {"id": 42, "title": "Test"},
    )
    assert payload["event"] == mod.EVENT_CREATED
    assert payload["source"] == "lumo"
    assert payload["opportunity"]["id"] == 42
    assert "sentAt" in payload


@pytest.mark.asyncio
async def test_post_webhook_success():
    settings = MagicMock(
        startify_catalog_webhook_url="https://api.startify.example/hook",
        partner_api_key="secret",
    )
    response = MagicMock(status_code=200, text="ok")

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(mod.httpx, "AsyncClient", return_value=mock_client):
        ok = await mod._post_webhook(
            mod.build_webhook_payload(mod.EVENT_CREATED, {"id": 1, "title": "X"})
        )

    assert ok is True
    mock_client.post.assert_awaited_once()
    call_kwargs = mock_client.post.await_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer secret"


@pytest.mark.asyncio
async def test_schedule_catalog_push_noop_when_not_configured():
    with patch.object(mod, "is_push_configured", return_value=False):
        mod.schedule_catalog_push([1, 2, 3])
    # no task created — should not raise

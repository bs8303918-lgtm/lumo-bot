"""Tests for Startify catalog push webhook."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import startify_catalog_push as mod


def test_is_push_configured_requires_url_and_key():
    settings = MagicMock(
        startify_catalog_push_enabled=True,
        startify_catalog_webhook_url="https://api-dev.aistartify.com/api/webhooks/lumo/catalog",
        partner_api_key="secret",
    )
    with patch.object(mod, "get_settings", return_value=settings):
        assert mod.is_push_configured() is True

    settings.partner_api_key = ""
    with patch.object(mod, "get_settings", return_value=settings):
        assert mod.is_push_configured() is False


def test_map_startify_type():
    assert mod.map_startify_type("грант") == "grant"
    assert mod.map_startify_type("стажировка") == "internship"
    assert mod.map_startify_type("хакатон") == "event"
    assert mod.map_startify_type("unknown") == "event"


def test_build_webhook_payload_shape():
    payload = mod.build_webhook_payload(
        mod.EVENT_CREATED,
        {"id": 42, "title": "Test", "type": "grant"},
    )
    assert payload["event"] == mod.EVENT_CREATED
    assert payload["source"] == "lumo-catalog"
    assert payload["opportunity"]["id"] == 42
    assert "sentAt" in payload


def test_serialize_for_startify_shape():
    entry = MagicMock()
    entry.id = 7
    entry.opportunity_type = "грант"
    entry.title = "A" * 100
    entry.description = "Desc"
    entry.deadline = "15 августа 2026"
    entry.requirements = "Team 2+"
    entry.application_url = "https://example.com"
    entry.message_link = "https://t.me/chan/1"
    entry.source_channel_name = "@chan"
    entry.is_active = True

    with patch.object(mod, "entry_all_tags", return_value=["KZ", "AgriTech"]):
        with patch.object(mod, "normalize_application_url", return_value="https://example.com"):
            with patch.object(mod, "pick_telegram_post_link", return_value="https://t.me/chan/1"):
                with patch.object(mod, "normalize_message_link", return_value=None):
                    with patch.object(mod, "clean_source_name", return_value="chan"):
                        data = mod.serialize_for_startify(entry)

    assert data["id"] == 7
    assert data["type"] == "grant"
    assert len(data["title"]) <= 80
    assert data["tags"] == ["KZ", "AgriTech"]
    assert data["isPremium"] is False
    assert data["isActive"] is True
    assert data["applicationUrl"] == "https://example.com"


@pytest.mark.asyncio
async def test_post_webhook_success():
    settings = MagicMock(
        startify_catalog_webhook_url="https://api-dev.aistartify.com/hook",
        partner_api_key="secret",
    )
    response = MagicMock(status_code=200, text='{"ok":true}')

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(mod, "get_settings", return_value=settings):
        with patch.object(mod.httpx, "AsyncClient", return_value=mock_client):
            ok = await mod._post_webhook(
                mod.build_webhook_payload(mod.EVENT_CREATED, {"id": 1, "title": "X"})
            )

    assert ok is True
    mock_client.post.assert_awaited_once()
    call_kwargs = mock_client.post.await_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer secret"


@pytest.mark.asyncio
async def test_post_webhook_no_retry_on_4xx():
    settings = MagicMock(
        startify_catalog_webhook_url="https://api-dev.aistartify.com/hook",
        partner_api_key="secret",
    )
    response = MagicMock(status_code=401, text='{"message":"Invalid"}')

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(mod, "get_settings", return_value=settings):
        with patch.object(mod.httpx, "AsyncClient", return_value=mock_client):
            ok = await mod._post_webhook(
                mod.build_webhook_payload(mod.EVENT_CREATED, {"id": 1})
            )

    assert ok is False
    assert mock_client.post.await_count == 1


@pytest.mark.asyncio
async def test_schedule_catalog_push_noop_when_not_configured():
    with patch.object(mod, "is_push_configured", return_value=False):
        mod.schedule_catalog_push([1, 2, 3])

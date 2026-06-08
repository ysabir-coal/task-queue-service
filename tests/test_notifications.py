"""Tests for webhook notifications."""

import pytest
from unittest.mock import AsyncMock, patch

from app.notifications import send_webhook, _compute_signature


class TestWebhookSignature:
    def test_compute_signature_is_deterministic(self):
        body = '{"task_id":"abc","status":"completed"}'
        sig1 = _compute_signature(body)
        sig2 = _compute_signature(body)
        assert sig1 == sig2

    def test_different_body_different_signature(self):
        sig1 = _compute_signature('{"a":1}')
        sig2 = _compute_signature('{"a":2}')
        assert sig1 != sig2


class TestSendWebhook:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        with patch("app.notifications.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            result = await send_webhook(
                "https://example.com/hook", "task-1", "completed", result={"ok": True}
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_4xx(self):
        with patch("app.notifications.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 403
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            result = await send_webhook(
                "https://example.com/hook", "task-1", "failed", error="boom"
            )
            assert result is False

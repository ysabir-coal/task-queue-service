"""Webhook notification sender."""

import hashlib
import hmac
import json
import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_webhook(
    callback_url: str,
    task_id: str,
    status: str,
    result: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
) -> bool:
    """Send a webhook notification for task completion.

    Signs the payload with HMAC-SHA256 using the configured secret.
    Returns True if delivery succeeded.
    """
    payload = {
        "task_id": task_id,
        "status": status,
        "result": result,
        "error": error,
    }
    body = json.dumps(payload, separators=(",", ":"))
    signature = _compute_signature(body)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Task-ID": task_id,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.notification_timeout) as client:
            response = await client.post(callback_url, content=body, headers=headers)
            if response.status_code >= 400:
                logger.warning(
                    "Webhook delivery failed: %s %s", response.status_code, callback_url
                )
                return False
            return True
    except httpx.TimeoutException:
        logger.warning("Webhook timed out: %s", callback_url)
        return False
    except Exception as e:
        logger.error("Webhook delivery error: %s", e)
        return False


def _compute_signature(body: str) -> str:
    """Compute HMAC-SHA256 signature for the webhook payload."""
    secret = settings.webhook_secret.encode()
    return hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()

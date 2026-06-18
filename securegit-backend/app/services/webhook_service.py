"""
Webhook Service — internal-only webhook dispatch.
Enforces LAN/localhost-only target URLs.
"""
import hashlib
import hmac
import json
import logging
import re
import urllib.parse
import requests
from datetime import datetime, timezone
from typing import Optional
from ..extensions import db
from ..models.enhancement_models import WebhookEndpoint

logger = logging.getLogger(__name__)

# Allow only localhost, LAN IPs, and .local domains
_ALLOWED_HOSTS_RE = re.compile(
    r'^(localhost|127\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|[a-z0-9\-]+\.local)$',
    re.IGNORECASE,
)


def _is_internal_url(url: str) -> bool:
    """Return True if the URL points to a LAN/localhost host."""
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ""
        return bool(_ALLOWED_HOSTS_RE.match(host))
    except Exception:
        return False


def _sign_payload(secret: str, payload: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def dispatch(endpoint: WebhookEndpoint, event: str, payload: dict) -> int:
    """
    Dispatch a webhook event to a single endpoint.
    Returns HTTP status code of the delivery (0 = connection error).
    """
    if not endpoint.is_active:
        return 0
    if event not in endpoint.events:
        return 0
    if not _is_internal_url(endpoint.target_url):
        logger.warning("Blocked external webhook URL: %s", endpoint.target_url)
        return 0

    body = json.dumps(payload, default=str).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-SecureGit-Event": event,
    }
    if endpoint.secret_hash:
        headers["X-SecureGit-Signature"] = _sign_payload(endpoint.secret_hash, body)

    try:
        resp = requests.post(endpoint.target_url, data=body, headers=headers, timeout=10)
        status = resp.status_code
    except requests.RequestException as e:
        logger.error("Webhook delivery failed to %s: %s", endpoint.target_url, e)
        status = 0

    # Update delivery status
    endpoint.last_delivery_at = datetime.now(timezone.utc)
    endpoint.last_delivery_status = status
    db.session.commit()
    return status


def dispatch_event(project_id: int, event: str, payload: dict) -> list[int]:
    """Dispatch an event to all active endpoints for a project."""
    endpoints = WebhookEndpoint.query.filter_by(
        project_id=project_id, is_active=True
    ).all()
    return [dispatch(ep, event, payload) for ep in endpoints]

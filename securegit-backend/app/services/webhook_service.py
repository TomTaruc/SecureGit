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
from requests.exceptions import ConnectTimeout, ConnectionError, SSLError, Timeout

logger = logging.getLogger(__name__)

def _classify_error(e: Exception) -> str:
    if isinstance(e, ConnectTimeout):
        return "Connection timeout — the target did not respond in time."
    if isinstance(e, SSLError):
        return f"TLS/SSL handshake failed: {e}"
    if isinstance(e, ConnectionError):
        msg = str(e)
        if "Name or service not known" in msg or "nodename nor servname" in msg:
            return f"DNS resolution failed: {msg}"
        if "Connection refused" in msg:
            return f"Connection refused: {msg}"
        return f"Connection error: {msg}"
    if isinstance(e, Timeout):
        return "Request timed out."
    return str(e)

# Allow only localhost, LAN IPs, and .local domains
_ALLOWED_HOSTS_RE = re.compile(
    r'^(localhost|127\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|[a-z0-9\-]+\.local)$',
    re.IGNORECASE,
)


import socket
import ipaddress

def _is_internal_url(url: str) -> bool:
    """Return True if the URL resolves strictly to a LAN/localhost IP."""
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ""
        
        # If it's literally a .local domain, we could let it pass
        # but to be truly secure against rebinding we must resolve it.
        # getaddrinfo resolves the hostname to IPs
        addr_info = socket.getaddrinfo(host, None)
        
        for info in addr_info:
            ip_str = info[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            # Must be a private, loopback, or link-local IP.
            if not (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local):
                return False
        return True
    except Exception:
        return False


def _sign_payload(secret: str, payload: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def dispatch(endpoint: WebhookEndpoint, event: str, payload: dict, return_error: bool = False):
    """
    Dispatch a webhook event to a single endpoint.
    Returns HTTP status code of the delivery (0 = connection error).
    """
    if not endpoint.is_active:
        return (0, "Webhook is not active") if return_error else 0
    if event not in endpoint.events:
        return (0, f"Event {event} not in configured events") if return_error else 0
    if not _is_internal_url(endpoint.target_url):
        logger.warning("Blocked external webhook URL: %s", endpoint.target_url)
        return (0, "Only internal LAN/localhost URLs are allowed") if return_error else 0

    body = json.dumps(payload, default=str).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-SecureGit-Event": event,
    }
    if endpoint.secret_hash:
        headers["X-SecureGit-Signature"] = _sign_payload(endpoint.secret_hash, body)

    error_msg = ""
    try:
        resp = requests.post(endpoint.target_url, data=body, headers=headers, timeout=10)
        status = resp.status_code
        if not (200 <= status < 300):
            error_msg = f"HTTP {status}: {resp.text[:200]}"
    except requests.RequestException as e:
        logger.error("Webhook delivery failed to %s: %s", endpoint.target_url, e)
        status = 0
        error_msg = _classify_error(e)

    # Update delivery status
    endpoint.last_delivery_at = datetime.now(timezone.utc)
    endpoint.last_delivery_status = status
    db.session.commit()
    
    if return_error:
        return status, error_msg
    return status


def dispatch_event(project_id: int, event: str, payload: dict) -> list[int]:
    """Dispatch an event to all active endpoints for a project."""
    endpoints = WebhookEndpoint.query.filter_by(
        project_id=project_id, is_active=True
    ).all()
    return [dispatch(ep, event, payload) for ep in endpoints]

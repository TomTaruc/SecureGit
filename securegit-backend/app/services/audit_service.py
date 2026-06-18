"""
Audit Service — writes to audit_log table.
Called from every route that mutates state.
"""
import logging
from typing import Optional
from flask import request
from ..extensions import db
from ..models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def log(
    actor_id: int,
    action: str,
    target_id: Optional[int] = None,
    target_type: Optional[str] = None,
    detail: Optional[str] = None,
    ip: Optional[str] = None,
) -> AuditLog:
    """
    Record an audit event. Automatically reads IP from Flask request context
    if ip is not explicitly provided.
    """
    if ip is None:
        try:
            ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            if ip and "," in ip:
                ip = ip.split(",")[0].strip()
        except RuntimeError:
            ip = None  # Outside request context

    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        target_id=target_id,
        target_type=target_type,
        detail=detail,
        ip_address=ip,
    )
    db.session.add(entry)
    # Flush to assign PK but let the calling route manage the transaction.
    # This prevents premature commits of partial route-level work.
    db.session.flush()
    logger.info("AUDIT actor=%d action=%s target=%s/%s", actor_id, action, target_type, target_id)
    return entry

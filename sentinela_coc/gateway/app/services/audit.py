# -*- coding: utf-8 -*-
"""Auditoría de autenticación: registra TODOS los eventos (W5.3 / WS-9)."""
import logging

from ..models import AuthAuditEvent

_logger = logging.getLogger("coc.gateway.audit")


def record(db, event_type, *, success=True, partner_id=None, identity_id=None,
           session_id=None, phone=None, device=None, ip=None, user_agent=None, detail=None):
    ev = AuthAuditEvent(
        event_type=event_type, success=success, partner_id=partner_id,
        identity_id=identity_id, session_id=session_id, phone=phone, device=device,
        ip=ip, user_agent=(user_agent or "")[:400] or None, detail=detail,
    )
    db.add(ev)
    db.flush()
    _logger.info("auth_event type=%s ok=%s phone=%s ip=%s device=%s detail=%s",
                 event_type, success, phone, ip, device, detail)
    return ev


def list_history(db, partner_id, limit=50, offset=0):
    """Historial de accesos del cliente (login/refresh/logout/new_device/...)."""
    return (db.query(AuthAuditEvent)
            .filter(AuthAuditEvent.partner_id == partner_id)
            .order_by(AuthAuditEvent.created_at.desc())
            .limit(limit).offset(offset).all())

# -*- coding: utf-8 -*-
"""Rate limiting + cooldown para OTP (por teléfono, IP y dispositivo).

Se calcula contando eventos de auditoría dentro de la ventana → reusa la auditoría
como fuente de verdad (todo intento queda registrado).
"""
from datetime import timedelta
from ..clock import utcnow

from sqlalchemy import func, select

from ..config import settings
from ..models import AuthAuditEvent


def _count(db, field, value, since, event_types):
    if not value:
        return 0
    q = (select(func.count())
         .select_from(AuthAuditEvent)
         .where(getattr(AuthAuditEvent, field) == value)
         .where(AuthAuditEvent.event_type.in_(event_types))
         .where(AuthAuditEvent.created_at >= since))
    return db.execute(q).scalar_one()


def check_otp_request_allowed(db, phone, ip, device):
    """Devuelve (allowed: bool, reason: str|None)."""
    now = utcnow()
    window_since = now - timedelta(seconds=settings.otp_rate_window_sec)
    cooldown_since = now - timedelta(seconds=settings.otp_cooldown_sec)

    if _count(db, "phone", phone, cooldown_since, ["otp_request"]) > 0:
        return False, "cooldown"
    if _count(db, "phone", phone, window_since, ["otp_request"]) >= settings.otp_max_per_phone:
        return False, "rate_phone"
    if _count(db, "ip", ip, window_since, ["otp_request"]) >= settings.otp_max_per_ip:
        return False, "rate_ip"
    if _count(db, "device", device, window_since, ["otp_request"]) >= settings.otp_max_per_device:
        return False, "rate_device"
    return True, None


def check_otp_verify_allowed(db, phone, ip):
    """Limita intentos de verificación abusivos por teléfono/IP en la ventana."""
    now = utcnow()
    window_since = now - timedelta(seconds=settings.otp_rate_window_sec)
    # 3 intentos por código * margen; cap duro por teléfono en la ventana.
    if _count(db, "phone", phone, window_since, ["otp_verify"]) >= (settings.otp_max_per_phone * settings.otp_max_attempts):
        return False, "rate_phone"
    if _count(db, "ip", ip, window_since, ["otp_verify"]) >= (settings.otp_max_per_ip * settings.otp_max_attempts):
        return False, "rate_ip"
    return True, None

# -*- coding: utf-8 -*-
"""Flujo OTP (W5.3): request/verify con hash-only, TTL, intentos, cooldown,
rate limiting (ip/teléfono/device) y auditoría completa. Proveedor desacoplado."""
from datetime import timedelta
from ..clock import utcnow

from ..config import settings
from ..models import OtpChallenge
from ..security.hashing import constant_eq, gen_otp, hash_secret
from . import audit, rate_limit, session_service


def request_otp(db, provider, phone, ip, device, channel="whatsapp"):
    allowed, reason = rate_limit.check_otp_request_allowed(db, phone, ip, device)
    if not allowed:
        audit.record(db, "otp_blocked", success=False, phone=phone, ip=ip, device=device, detail=reason)
        return {"ok": False, "reason": reason}

    code = gen_otp(settings.otp_length)
    now = utcnow()
    db.add(OtpChallenge(
        phone=phone, channel=channel,
        code_hash=hash_secret(code, settings.jwt_secret),   # SOLO hash
        max_attempts=settings.otp_max_attempts,
        expires_at=now + timedelta(seconds=settings.otp_ttl_sec),
        device=device, ip=ip,
    ))
    db.flush()
    audit.record(db, "otp_request", success=True, phone=phone, ip=ip, device=device)

    try:
        sent = provider.send(phone, code, channel)
    except Exception as e:  # no filtrar errores del proveedor al cliente
        audit.record(db, "otp_sent", success=False, phone=phone, ip=ip, device=device, detail=str(e)[:200])
        return {"ok": True}
    audit.record(db, "otp_sent", success=bool(sent), phone=phone, ip=ip, device=device)
    return {"ok": True}


def consume_otp(db, phone, code, ip, device):
    """Valida y CONSUME un OTP (sin crear sesión). Reutilizado por login, recuperación
    de contraseña y cambio de teléfono. Devuelve (ok: bool, reason: str|None)."""
    allowed, reason = rate_limit.check_otp_verify_allowed(db, phone, ip)
    if not allowed:
        audit.record(db, "otp_verify", success=False, phone=phone, ip=ip, device=device, detail="rate:" + reason)
        return False, "rate"

    now = utcnow()
    ch = (db.query(OtpChallenge)
          .filter(OtpChallenge.phone == phone,
                  OtpChallenge.consumed == False,  # noqa: E712
                  OtpChallenge.expires_at > now)
          .order_by(OtpChallenge.created_at.desc())
          .first())
    if not ch:
        audit.record(db, "otp_verify", success=False, phone=phone, ip=ip, device=device, detail="no_challenge")
        return False, "invalid"

    ch.attempts += 1
    if not constant_eq(hash_secret(code, settings.jwt_secret), ch.code_hash):
        if ch.attempts >= ch.max_attempts:
            ch.consumed = True  # bloquea el código tras N intentos
        audit.record(db, "otp_verify", success=False, phone=phone, ip=ip, device=device,
                     detail="mismatch %d/%d" % (ch.attempts, ch.max_attempts))
        db.flush()
        return False, "invalid"

    ch.consumed = True  # single-use
    audit.record(db, "otp_verify", success=True, phone=phone, ip=ip, device=device)
    return True, None


def verify_otp(db, odoo, phone, code, ip, device, ua, notifier=None):
    ok, reason = consume_otp(db, phone, code, ip, device)
    if not ok:
        return {"ok": False, "error": "rate" if reason == "rate" else "invalid"}

    partner_id = odoo.resolve_phone(phone)
    if not partner_id:
        # Teléfono verificado pero sin cliente: respuesta neutra (no se filtra existencia).
        audit.record(db, "login", success=False, phone=phone, ip=ip, device=device, detail="no_partner")
        return {"ok": False, "error": "invalid"}

    identity = session_service.get_or_create_identity(db, phone, partner_id)
    tokens = session_service.create_session(db, odoo, identity, partner_id, ip, device, ua, notifier=notifier)
    if not tokens:
        audit.record(db, "login", success=False, phone=phone, ip=ip, device=device,
                     partner_id=partner_id, detail="odoo_open_failed")
        return {"ok": False, "error": "odoo_unavailable"}

    audit.record(db, "login", success=True, phone=phone, ip=ip, device=device,
                 partner_id=partner_id, identity_id=identity.id, session_id=tokens["session_id"])
    return {"ok": True, **tokens}

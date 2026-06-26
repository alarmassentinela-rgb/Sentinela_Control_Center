# -*- coding: utf-8 -*-
"""Contraseñas (W5.8): set/cambio, login por contraseña, recuperación por OTP.

Al cambiar credenciales se REVOCAN todas las sesiones (excepto la actual en cambio).
"""
from ..models import PortalIdentity
from ..security.passwords import hash_password, validate_policy, verify_password
from . import audit, otp_service, session_service


def set_or_change_password(db, odoo, identity, new_password, current_password=None,
                           keep_session_id=None, ip=None, ua=None):
    if identity.password_hash:
        if current_password is None:
            return {"ok": False, "error": "current_required"}
        if not verify_password(current_password, identity.password_hash):
            audit.record(db, "password_change", success=False, identity_id=identity.id,
                         partner_id=identity.partner_id, ip=ip, user_agent=ua, detail="bad_current")
            return {"ok": False, "error": "bad_current"}
    ok, reason = validate_policy(new_password)
    if not ok:
        return {"ok": False, "error": "policy", "detail": reason}
    identity.password_hash = hash_password(new_password)
    db.flush()
    n = session_service.revoke_all_on_credential_change(db, odoo, identity.id,
                                                        keep_session_id=keep_session_id, ip=ip, ua=ua)
    audit.record(db, "password_change", success=True, identity_id=identity.id,
                 partner_id=identity.partner_id, ip=ip, user_agent=ua, detail="revoked=%d" % n)
    return {"ok": True, "revoked_sessions": n}


def login_password(db, odoo, phone, password, ip, device, ua, notifier=None):
    ident = db.query(PortalIdentity).filter_by(phone=phone).one_or_none()
    if not ident or not ident.password_hash or not verify_password(password, ident.password_hash):
        audit.record(db, "login", success=False, phone=phone, ip=ip, device=device, detail="bad_password")
        return {"ok": False, "error": "invalid"}
    partner_id = ident.partner_id or odoo.resolve_phone(phone)
    if not partner_id:
        return {"ok": False, "error": "invalid"}
    tokens = session_service.create_session(db, odoo, ident, partner_id, ip, device, ua, notifier=notifier)
    if not tokens:
        return {"ok": False, "error": "odoo_unavailable"}
    audit.record(db, "login", success=True, phone=phone, partner_id=partner_id,
                 identity_id=ident.id, session_id=tokens["session_id"], ip=ip, device=device)
    return {"ok": True, **tokens}


def recover_request(db, provider, phone, ip, device):
    # Reusa el flujo OTP (rate-limit/cooldown/auditoría incluidos). Respuesta neutra.
    return otp_service.request_otp(db, provider, phone, ip, device)


def recover_confirm(db, odoo, phone, code, new_password, ip, device, ua):
    ok, reason = otp_service.consume_otp(db, phone, code, ip, device)
    if not ok:
        return {"ok": False, "error": "rate" if reason == "rate" else "invalid"}
    okp, preason = validate_policy(new_password)
    if not okp:
        return {"ok": False, "error": "policy", "detail": preason}
    partner_id = odoo.resolve_phone(phone)
    if not partner_id:
        audit.record(db, "password_recover", success=False, phone=phone, ip=ip, detail="no_partner")
        return {"ok": False, "error": "invalid"}
    ident = session_service.get_or_create_identity(db, phone, partner_id)
    ident.password_hash = hash_password(new_password)
    db.flush()
    n = session_service.revoke_all_on_credential_change(db, odoo, ident.id, ip=ip, ua=ua)
    audit.record(db, "password_recover", success=True, phone=phone, partner_id=partner_id,
                 identity_id=ident.id, ip=ip, detail="revoked=%d" % n)
    return {"ok": True, "revoked_sessions": n}

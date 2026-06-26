# -*- coding: utf-8 -*-
"""Cambio seguro de teléfono con doble verificación (W5.8).

Verifica OTP en el teléfono NUEVO siempre; y en el ACTUAL si la identidad ya tenía
teléfono (doble verificación). Al confirmar, actualiza Odoo + revoca todas las sesiones.
"""
from . import audit, otp_service, session_service


def request_change(db, provider, identity, new_phone, ip, device):
    otp_service.request_otp(db, provider, new_phone, ip, device)
    double = bool(identity.phone)
    if double:
        otp_service.request_otp(db, provider, identity.phone, ip, device)
    audit.record(db, "phone_change_request", success=True, identity_id=identity.id,
                 partner_id=identity.partner_id, ip=ip, detail="double=%s new=%s" % (double, new_phone))
    return {"ok": True, "double_verification": double}


def confirm_change(db, odoo, identity, new_phone, code_new, code_current, ip, device, ua):
    # Validar PRESENCIA antes de consumir, para no desperdiciar el código nuevo.
    if identity.phone and not code_current:
        return {"ok": False, "error": "current_code_required"}
    okn, rn = otp_service.consume_otp(db, new_phone, code_new, ip, device)
    if not okn:
        return {"ok": False, "error": "new_" + (rn or "invalid")}
    if identity.phone:   # doble verificación
        okc, rc = otp_service.consume_otp(db, identity.phone, code_current, ip, device)
        if not okc:
            return {"ok": False, "error": "current_" + (rc or "invalid")}
    res = odoo.set_phone(identity.partner_id, new_phone)
    if not res or not res.get("ok"):
        return {"ok": False, "error": "odoo_failed"}
    identity.phone = new_phone
    db.flush()
    n = session_service.revoke_all_on_credential_change(db, odoo, identity.id, ip=ip, ua=ua)
    audit.record(db, "phone_change", success=True, identity_id=identity.id,
                 partner_id=identity.partner_id, ip=ip, detail="revoked=%d new=%s" % (n, new_phone))
    return {"ok": True, "revoked_sessions": n}

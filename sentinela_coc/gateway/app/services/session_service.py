# -*- coding: utf-8 -*-
"""Sesiones cortas: access JWT + refresh rotativo (un solo uso) con detección de reuse.

La autorización vive en Odoo (sesión efímera del usuario portal vía OdooClient).
"""
from datetime import timedelta
from ..clock import utcnow

from sqlalchemy import update

from ..config import settings
from ..models import Device, PortalIdentity, PortalSession, RefreshToken
from ..security.hashing import gen_token, hash_secret
from ..security.tokens import make_access_token
from . import audit


def get_or_create_identity(db, phone, partner_id, email=None):
    ident = db.query(PortalIdentity).filter_by(phone=phone).one_or_none()
    if ident:
        if partner_id and ident.partner_id != partner_id:
            ident.partner_id = partner_id
        return ident
    ident = PortalIdentity(phone=phone, partner_id=partner_id, email=email)
    db.add(ident)
    db.flush()
    return ident


def get_session(db, sid):
    if not sid:
        return None
    return db.query(PortalSession).filter_by(id=sid).one_or_none()


def _tokens(db, sess):
    access, jti = make_access_token(sess.id, sess.partner_id, sess.odoo_uid,
                                    settings.jwt_secret, settings.jwt_access_ttl_min)
    sess.access_jti = jti
    refresh_raw = gen_token()
    db.add(RefreshToken(
        session_id=sess.id, family=sess.refresh_family,
        token_hash=hash_secret(refresh_raw, settings.jwt_secret),
        expires_at=utcnow() + timedelta(days=settings.jwt_refresh_ttl_days),
    ))
    db.flush()
    return {"access_token": access, "refresh_token": refresh_raw, "token_type": "bearer",
            "expires_in": settings.jwt_access_ttl_min * 60, "session_id": sess.id}


def _touch_device(db, identity_id, device_id, label, ip, ua):
    """Upsert del dispositivo. Devuelve (device, es_nuevo)."""
    if not device_id:
        return None, False
    dev = db.query(Device).filter_by(identity_id=identity_id, device_id=device_id).one_or_none()
    is_new = dev is None
    if is_new:
        dev = Device(identity_id=identity_id, device_id=device_id, label=label or device_id,
                     last_ip=ip, last_user_agent=(ua or "")[:400] or None)
        db.add(dev)
    else:
        dev.last_seen = utcnow()
        dev.last_ip = ip
        dev.last_user_agent = (ua or "")[:400] or None
    db.flush()
    return dev, is_new


def create_session(db, odoo, identity, partner_id, ip, device, ua, notifier=None):
    res = odoo.open_session(partner_id, settings.jwt_access_ttl_min * 60, device, ip, ua)
    if not res or not res.get("ok"):
        return None
    now = utcnow()
    sess = PortalSession(
        identity_id=identity.id, partner_id=partner_id,
        odoo_uid=res.get("uid"), odoo_session_id=res.get("session_id"),
        device_id=device, device_label=device, ip=ip, user_agent=(ua or "")[:400] or None,
        last_seen_at=now, expires_at=now + timedelta(days=settings.jwt_refresh_ttl_days),
    )
    db.add(sess)
    db.flush()
    _dev, is_new_device = _touch_device(db, identity.id, device, device, ip, ua)
    if is_new_device:
        audit.record(db, "login_new_device", success=True, identity_id=identity.id,
                     partner_id=partner_id, session_id=sess.id, device=device, ip=ip, user_agent=ua)
        if notifier:
            try:
                notifier.notify_new_login(identity, device or "desconocido", ip)
            except Exception:
                pass
    return _tokens(db, sess)


def serialize_session(s, current_sid=None):
    return {
        "id": s.id,
        "device": s.device_label or s.device_id,
        "ip": s.ip,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "last_seen_at": s.last_seen_at.isoformat() if s.last_seen_at else None,
        "current": s.id == current_sid,
    }


def list_active_sessions(db, partner_id):
    return (db.query(PortalSession)
            .filter(PortalSession.partner_id == partner_id, PortalSession.revoked.is_(False))
            .order_by(PortalSession.created_at.desc()).all())


def close_session_by_id(db, odoo, partner_id, sid, ip=None, ua=None):
    s = get_session(db, sid)
    if not s or s.partner_id != partner_id:   # ownership check
        return False
    return revoke_session(db, odoo, s, event="logout", ip=ip, ua=ua)


def close_all_for_partner(db, odoo, partner_id, except_sid=None, ip=None, ua=None):
    n = 0
    for s in db.query(PortalSession).filter_by(partner_id=partner_id, revoked=False).all():
        if except_sid and s.id == except_sid:
            continue
        if revoke_session(db, odoo, s, event="revoke_all", ip=ip, ua=ua):
            n += 1
    return n


def revoke_all_on_credential_change(db, odoo, identity_id, keep_session_id=None, ip=None, ua=None):
    """Llamado por W5.8 al cambiar credenciales críticas (contraseña, etc.)."""
    n = 0
    for s in db.query(PortalSession).filter_by(identity_id=identity_id, revoked=False).all():
        if keep_session_id and s.id == keep_session_id:
            continue
        if revoke_session(db, odoo, s, event="revoke_credentials_change", ip=ip, ua=ua):
            n += 1
    return n


def _revoke_family(db, odoo, family):
    for s in db.query(PortalSession).filter_by(refresh_family=family).all():
        if not s.revoked:
            s.revoked = True
            s.revoked_at = utcnow()
            if s.odoo_session_id:
                try:
                    odoo.close_session(s.odoo_session_id)
                except Exception:
                    pass
    for t in db.query(RefreshToken).filter_by(family=family, used=False).all():
        t.used = True
    db.flush()


def refresh_session(db, odoo, refresh_raw, ip=None, ua=None):
    h = hash_secret(refresh_raw, settings.jwt_secret)
    rt = db.query(RefreshToken).filter_by(token_hash=h).one_or_none()
    if not rt:
        return {"ok": False, "error": "invalid"}
    sess = get_session(db, rt.session_id)
    now = utcnow()
    # Claim ATÓMICO del refresh: seguro ante refresh CONCURRENTE (solo uno gana
    # la carrera; el UPDATE..WHERE used=false bloquea la fila en Postgres).
    claimed = db.execute(
        update(RefreshToken)
        .where(RefreshToken.id == rt.id, RefreshToken.used.is_(False))
        .values(used=True)
    ).rowcount
    if not claimed:
        # Ya consumido -> reuse (posible robo): revoca toda la familia.
        _revoke_family(db, odoo, rt.family)
        audit.record(db, "refresh_reuse", success=False, session_id=rt.session_id,
                     partner_id=sess.partner_id if sess else None, ip=ip, user_agent=ua,
                     detail="refresh token reuse -> familia revocada")
        return {"ok": False, "error": "reuse"}
    if not sess or sess.revoked or rt.expires_at <= now:
        return {"ok": False, "error": "invalid"}
    # Renovar la sesión Odoo efímera (mantenerla corta).
    new = odoo.open_session(sess.partner_id, settings.jwt_access_ttl_min * 60, sess.device_label, ip, ua)
    if new and new.get("ok"):
        old = sess.odoo_session_id
        sess.odoo_session_id = new.get("session_id")
        sess.odoo_uid = new.get("uid")
        if old:
            try:
                odoo.close_session(old)
            except Exception:
                pass
    sess.last_seen_at = now
    out = _tokens(db, sess)
    audit.record(db, "refresh", success=True, session_id=sess.id, partner_id=sess.partner_id, ip=ip, user_agent=ua)
    return {"ok": True, **out}


def revoke_session(db, odoo, sess, event="logout", ip=None, ua=None):
    if not sess or sess.revoked:
        return False
    sess.revoked = True
    sess.revoked_at = utcnow()
    if sess.odoo_session_id:
        try:
            odoo.close_session(sess.odoo_session_id)
        except Exception:
            pass
    for t in db.query(RefreshToken).filter_by(session_id=sess.id, used=False).all():
        t.used = True
    audit.record(db, event, success=True, session_id=sess.id, partner_id=sess.partner_id, ip=ip, user_agent=ua)
    db.flush()
    return True


def revoke_all(db, odoo, partner_id, ip=None, ua=None):
    n = 0
    for s in db.query(PortalSession).filter_by(partner_id=partner_id, revoked=False).all():
        if revoke_session(db, odoo, s, event="revoke_all", ip=ip, ua=ua):
            n += 1
    return n

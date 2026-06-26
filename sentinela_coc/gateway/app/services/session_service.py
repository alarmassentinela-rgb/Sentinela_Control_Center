# -*- coding: utf-8 -*-
"""Sesiones cortas: access JWT + refresh rotativo (un solo uso) con detección de reuse.

La autorización vive en Odoo (sesión efímera del usuario portal vía OdooClient).
"""
from datetime import timedelta
from ..clock import utcnow

from sqlalchemy import update

from ..config import settings
from ..models import PortalIdentity, PortalSession, RefreshToken
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


def create_session(db, odoo, identity, partner_id, ip, device, ua):
    res = odoo.open_session(partner_id, settings.jwt_access_ttl_min * 60, device, ip, ua)
    if not res or not res.get("ok"):
        return None
    now = utcnow()
    sess = PortalSession(
        identity_id=identity.id, partner_id=partner_id,
        odoo_uid=res.get("uid"), odoo_session_id=res.get("session_id"),
        device_label=device, ip=ip, user_agent=(ua or "")[:400] or None,
        last_seen_at=now, expires_at=now + timedelta(days=settings.jwt_refresh_ttl_days),
    )
    db.add(sess)
    db.flush()
    return _tokens(db, sess)


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

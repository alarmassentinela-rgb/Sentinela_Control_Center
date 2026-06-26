# -*- coding: utf-8 -*-
"""Magic Links de UN SOLO USO con expiración corta (W5.10).

Solo para firma de documentos y autorizaciones. Token guardado como hash;
consumo atómico (un solo uso); expiración corta.
"""
from datetime import timedelta

from sqlalchemy import update

from ..clock import utcnow
from ..config import settings
from ..models import MagicLinkToken
from ..security.hashing import gen_token, hash_secret
from . import audit


def issue(db, purpose, partner_id, res_model=None, res_id=None, ttl_sec=600):
    raw = gen_token()
    db.add(MagicLinkToken(
        token_hash=hash_secret(raw, settings.jwt_secret),
        purpose=purpose, partner_id=partner_id, res_model=res_model, res_id=res_id,
        expires_at=utcnow() + timedelta(seconds=ttl_sec),
    ))
    db.flush()
    return raw


def consume(db, token, ip=None, ua=None):
    ml = db.query(MagicLinkToken).filter_by(
        token_hash=hash_secret(token or "", settings.jwt_secret)).one_or_none()
    if not ml:
        return {"ok": False, "error": "invalid"}
    if ml.expires_at <= utcnow():
        return {"ok": False, "error": "expired"}
    # Claim atómico: UN SOLO USO (seguro ante consumo concurrente).
    claimed = db.execute(
        update(MagicLinkToken)
        .where(MagicLinkToken.id == ml.id, MagicLinkToken.used.is_(False))
        .values(used=True, used_at=utcnow())
    ).rowcount
    if not claimed:
        audit.record(db, "magic_link_reuse", success=False, partner_id=ml.partner_id,
                     ip=ip, user_agent=ua, detail=ml.purpose)
        return {"ok": False, "error": "used"}
    audit.record(db, "magic_link_use", success=True, partner_id=ml.partner_id,
                 ip=ip, user_agent=ua, detail=ml.purpose)
    return {"ok": True, "purpose": ml.purpose, "partner_id": ml.partner_id,
            "res_model": ml.res_model, "res_id": ml.res_id}

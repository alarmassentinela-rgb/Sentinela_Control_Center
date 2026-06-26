# -*- coding: utf-8 -*-
"""Access JWT (corto). Refresh es opaco (ver services/session)."""
from datetime import datetime, timedelta, timezone

from jose import jwt

ALG = "HS256"


def make_access_token(sid: str, partner_id: int, odoo_uid: int | None,
                      secret: str, ttl_min: int) -> tuple[str, str]:
    """Devuelve (token, jti). El jti = sid de la sesión (revocación inmediata)."""
    now = datetime.now(timezone.utc)
    claims = {
        "sid": sid,
        "jti": sid,
        "partner_id": partner_id,
        "odoo_uid": odoo_uid,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_min)).timestamp()),
        "typ": "access",
    }
    return jwt.encode(claims, secret, algorithm=ALG), sid


def decode_access_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=[ALG])

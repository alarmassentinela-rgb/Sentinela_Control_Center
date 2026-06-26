# -*- coding: utf-8 -*-
"""Inyección de dependencias (sustituibles en pruebas)."""
from fastapi import Depends, Header, HTTPException

from .clients.odoo import HttpOdooClient
from .config import settings
from .db import SessionLocal
from .providers.factory import get_notifier as _notifier
from .providers.factory import get_otp_provider as _otp_provider
from .security.tokens import decode_access_token


def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_otp_provider():
    return _otp_provider()


def get_notifier():
    return _notifier()


def current_session(authorization: str | None = Header(default=None), db=Depends(get_db)):
    """Valida el access JWT y carga la sesión. El access es REVOCABLE: se verifica
    en DB que la sesión exista y no esté revocada en cada request."""
    from .services import session_service
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing_token")
    try:
        claims = decode_access_token(authorization.split(" ", 1)[1], settings.jwt_secret)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_token")
    sess = session_service.get_session(db, claims.get("sid"))
    if not sess or sess.revoked:
        raise HTTPException(status_code=401, detail="session_revoked")
    return sess


_odoo = None


def get_odoo_client():
    global _odoo
    if _odoo is None:
        _odoo = HttpOdooClient(settings.odoo_base_url, settings.coc_shared_secret)
    return _odoo

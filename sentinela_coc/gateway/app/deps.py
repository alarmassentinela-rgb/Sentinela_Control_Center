# -*- coding: utf-8 -*-
"""Inyección de dependencias (sustituibles en pruebas)."""
from .clients.odoo import HttpOdooClient
from .config import settings
from .db import SessionLocal
from .providers.factory import get_otp_provider as _otp_provider


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


_odoo = None


def get_odoo_client():
    global _odoo
    if _odoo is None:
        _odoo = HttpOdooClient(settings.odoo_base_url, settings.coc_shared_secret)
    return _odoo

# -*- coding: utf-8 -*-
"""Conexión a la base de datos PROPIA del gateway (identidad/sesiones/OTP/auditoría).

NO contiene datos de negocio (esos viven en Odoo). Postgres dedicado.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

engine = create_engine(settings.gateway_db_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """Dependencia FastAPI: una sesión por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -*- coding: utf-8 -*-
"""Fixtures de prueba: SQLite en memoria + proveedor OTP Mock + Odoo Fake.

Permite validar TODO el flujo de autenticación SIN servicios externos.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import deps
from app.clients.odoo import FakeOdooClient
from app.config import settings
from app.db import Base
from app.main import app
from app.providers.notifier_mock import MockLoginNotifier
from app.providers.otp_mock import MockOtpProvider

_TUNABLES = [
    "otp_cooldown_sec", "otp_max_per_phone", "otp_max_per_ip", "otp_max_per_device",
    "otp_ttl_sec", "otp_max_attempts", "jwt_access_ttl_min", "jwt_secret", "coc_shared_secret",
]


class Ctx:
    def __init__(self, client, mock, fake, Session, notifier):
        self.client = client
        self.mock = mock
        self.fake = fake
        self.Session = Session
        self.notifier = notifier


@pytest.fixture
def ctx():
    saved = {k: getattr(settings, k) for k in _TUNABLES}
    settings.jwt_secret = "test-pepper"
    settings.otp_cooldown_sec = 0
    settings.otp_max_per_phone = 100
    settings.otp_max_per_ip = 1000
    settings.otp_max_per_device = 1000
    settings.otp_ttl_sec = 300
    settings.otp_max_attempts = 3
    settings.jwt_access_ttl_min = 15
    settings.coc_shared_secret = "test-secret"

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def override_db():
        db = Session()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    mock = MockOtpProvider()
    fake = FakeOdooClient(phone_map={"+528680000001": 25757, "+528680000002": 25758})
    notifier = MockLoginNotifier()
    app.dependency_overrides[deps.get_db] = override_db
    app.dependency_overrides[deps.get_otp_provider] = lambda: mock
    app.dependency_overrides[deps.get_odoo_client] = lambda: fake
    app.dependency_overrides[deps.get_notifier] = lambda: notifier

    with TestClient(app) as client:
        yield Ctx(client, mock, fake, Session, notifier)

    app.dependency_overrides.clear()
    for k, v in saved.items():
        setattr(settings, k, v)

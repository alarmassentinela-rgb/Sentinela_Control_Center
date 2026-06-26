# -*- coding: utf-8 -*-
"""W5.7 — E2E Gateway ↔ Odoo (STAGING) con datos reales.

Solo corre con COC_E2E=1 (necesita Odoo STAGING + secreto compartido). OTP sigue
mockeado (EvoApi intercambiable); el cliente Odoo es el REAL (HttpOdooClient).

Env:
  COC_E2E=1
  COC_ODOO_BASE_URL=http://192.168.3.2:8075
  COC_COC_SHARED_SECRET=<secreto>
  COC_E2E_MAP={"existing_preexisting":{"partner_id":..,"phone":".."}, ...}
"""
import json
import os
import threading

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

pytestmark = pytest.mark.skipif(os.environ.get("COC_E2E") != "1",
                                reason="e2e contra STAGING (set COC_E2E=1)")

from app import deps                                   # noqa: E402
from app.clients.odoo import HttpOdooClient            # noqa: E402
from app.config import settings                        # noqa: E402
from app.db import Base                                # noqa: E402
from app.main import app                               # noqa: E402
from app.models import PortalSession                   # noqa: E402
from app.providers.otp_mock import MockOtpProvider     # noqa: E402
from app.security.tokens import decode_access_token    # noqa: E402

ODOO = os.environ.get("COC_ODOO_BASE_URL", "http://192.168.3.2:8075")
SECRET = os.environ.get("COC_COC_SHARED_SECRET", "")
E2EMAP = json.loads(os.environ.get("COC_E2E_MAP", "{}"))


@pytest.fixture
def env():
    settings.jwt_secret = "e2e-pepper"
    settings.otp_cooldown_sec = 0
    settings.otp_max_per_phone = 100
    settings.otp_max_per_ip = 1000
    settings.otp_max_per_device = 1000
    settings.otp_ttl_sec = 300
    settings.otp_max_attempts = 3
    settings.jwt_access_ttl_min = 15

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def odb():
        d = Session()
        try:
            yield d
            d.commit()
        except Exception:
            d.rollback()
            raise
        finally:
            d.close()

    mock = MockOtpProvider()
    real = HttpOdooClient(ODOO, SECRET)
    app.dependency_overrides[deps.get_db] = odb
    app.dependency_overrides[deps.get_otp_provider] = lambda: mock
    app.dependency_overrides[deps.get_odoo_client] = lambda: real
    with TestClient(app) as c:
        yield c, mock, Session, real
    app.dependency_overrides.clear()


def _login(c, mock, phone):
    assert c.post("/v1/auth/otp/request", json={"phone": phone, "device": "e2e"}).status_code == 200
    code = mock.last_code(phone)
    assert code, "el Mock no entregó código"
    return c.post("/v1/auth/otp/verify", json={"phone": phone, "code": code, "device": "e2e"})


@pytest.mark.parametrize("scenario", ["existing_preexisting", "empresarial", "multi", "suspended", "new"])
def test_login_profiles_e2e(env, scenario):
    if scenario not in E2EMAP:
        pytest.skip(f"{scenario} no disponible en STAGING")
    c, mock, Session, real = env
    info = E2EMAP[scenario]
    v = _login(c, mock, info["phone"])
    assert v.status_code == 200, v.text
    claims = decode_access_token(v.json()["access_token"], settings.jwt_secret)
    assert claims["partner_id"] == info["partner_id"]
    # La sesión Odoo REAL representa al partner correcto (record rules vía /v1/me)
    with Session() as s:
        ps = s.query(PortalSession).order_by(PortalSession.created_at.desc()).first()
        sid = ps.odoo_session_id
    me = httpx.get(f"{ODOO}/v1/me", cookies={"session_id": sid}, timeout=10)
    assert me.status_code == 200 and me.json().get("id") == info["partner_id"]
    real.close_session(sid)


def test_lazy_user_concurrency_e2e(env):
    if "new" not in E2EMAP:
        pytest.skip("sin partner 'new'")
    c, mock, Session, real = env
    pid = E2EMAP["new"]["partner_id"]
    results = []

    def op():
        results.append(real.open_session(pid, 300, "e2e", None, None))

    ths = [threading.Thread(target=op) for _ in range(5)]
    [t.start() for t in ths]
    [t.join() for t in ths]
    oks = [r for r in results if r and r.get("ok")]
    assert len(oks) == 5, results
    for r in oks:
        real.close_session(r["session_id"])


def test_refresh_single_use_and_reuse_e2e(env):
    c, mock, Session, real = env
    phone = E2EMAP["existing_preexisting"]["phone"]
    rt1 = _login(c, mock, phone).json()["refresh_token"]
    r1 = c.post("/v1/auth/refresh", json={"refresh_token": rt1})
    assert r1.status_code == 200
    rt2 = r1.json()["refresh_token"]
    assert c.post("/v1/auth/refresh", json={"refresh_token": rt1}).status_code == 401   # reuse
    assert c.post("/v1/auth/refresh", json={"refresh_token": rt2}).status_code == 401   # familia revocada


def test_logout_during_active_sessions_e2e(env):
    c, mock, Session, real = env
    phone = E2EMAP["existing_preexisting"]["phone"]
    s1 = _login(c, mock, phone).json()
    s2 = _login(c, mock, phone).json()
    assert c.post("/v1/auth/logout", headers={"Authorization": "Bearer " + s1["access_token"]}).status_code == 200
    assert c.post("/v1/auth/refresh", json={"refresh_token": s1["refresh_token"]}).status_code == 401
    assert c.post("/v1/auth/refresh", json={"refresh_token": s2["refresh_token"]}).status_code == 200

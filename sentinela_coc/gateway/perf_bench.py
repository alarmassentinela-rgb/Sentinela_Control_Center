# -*- coding: utf-8 -*-
"""Micro-benchmark del Gateway (in-process, mocks). Ejecutar: python perf_bench.py"""
import time

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

settings.jwt_secret = "perf"
settings.otp_cooldown_sec = 0
settings.otp_max_per_phone = 10 ** 9
settings.otp_max_per_ip = 10 ** 9
settings.otp_max_per_device = 10 ** 9

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, future=True)


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
fake = FakeOdooClient(phone_map={})
app.dependency_overrides[deps.get_db] = odb
app.dependency_overrides[deps.get_otp_provider] = lambda: mock
app.dependency_overrides[deps.get_odoo_client] = lambda: fake
app.dependency_overrides[deps.get_notifier] = lambda: MockLoginNotifier()

c = TestClient(app)
N = 100

t0 = time.perf_counter()
toks = []
for i in range(N):
    ph = "+5200000%05d" % i
    fake.phone_map[ph] = 1000 + i
    c.post("/v1/auth/otp/request", json={"phone": ph})
    code = mock.last_code(ph)
    r = c.post("/v1/auth/otp/verify", json={"phone": ph, "code": code})
    toks.append(r.json()["access_token"])
dt = time.perf_counter() - t0
print("LOGIN        n=%d total=%.3fs avg=%.2f ms" % (N, dt, dt / N * 1000))

t0 = time.perf_counter()
for tk in toks:
    c.get("/v1/sessions", headers={"Authorization": "Bearer " + tk})
dt = time.perf_counter() - t0
print("SESSIONS_GET n=%d total=%.3fs avg=%.2f ms" % (len(toks), dt, dt / len(toks) * 1000))

t0 = time.perf_counter()
for _ in range(500):
    c.get("/health")
dt = time.perf_counter() - t0
print("HEALTH       n=500 avg=%.2f ms" % (dt / 500 * 1000))

# -*- coding: utf-8 -*-
"""Smoke test del gateway (WS-7): health responde y propaga X-Request-Id."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "coc-gateway"
    assert "X-Request-Id" in r.headers


def test_readyz_ok():
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"

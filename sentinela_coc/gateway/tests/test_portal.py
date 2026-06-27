# -*- coding: utf-8 -*-
"""Sprint 1 — recursos de negocio del Portal (proxy act-as + dashboard agregado + cache).

Valida envoltura {data, meta}, agregación del dashboard con "Próximas acciones",
caché TTL del dashboard, proxy de PDF y mapeo de sesión expirada. Sin Odoo real
(FakeOdooClient con respuestas canned).
"""
import pytest

from app.services.cache import cache

PHONE = "+528680000001"   # -> partner 25757


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _login(ctx):
    ctx.client.post("/v1/auth/otp/request", json={"phone": PHONE, "device": "d"})
    code = ctx.mock.last_code(PHONE)
    r = ctx.client.post("/v1/auth/otp/verify", json={"phone": PHONE, "code": code, "device": "d"})
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": "Bearer %s" % tok}


def test_requires_auth(ctx):
    assert ctx.client.get("/v1/services").status_code == 401


def test_services_envelope_and_meta(ctx):
    tok = _login(ctx)
    ctx.fake.json_responses["/v1/services"] = (200, {
        "items": [{"id": 1, "reference": "SUB-1", "status": "active",
                   "service_type": "alarm", "service_type_label": "Alarma", "plan": "Plan X"}],
        "count": 1})
    r = ctx.client.get("/v1/services", headers=_h(tok))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["count"] == 1
    assert body["meta"]["server_time"] and body["meta"]["request_id"]


def test_dashboard_aggregation_and_next_actions(ctx):
    tok = _login(ctx)
    ctx.fake.json_responses["/v1/services"] = (200, {"items": [
        {"id": 1, "reference": "SUB-1", "status": "suspended", "service_type": "internet",
         "service_type_label": "Internet", "plan": "100M"},
        {"id": 2, "reference": "SUB-2", "status": "active", "service_type": "alarm",
         "service_type_label": "Alarma", "plan": "Monitoreo"},
        {"id": 3, "reference": "SUB-3", "status": "pending_signature", "service_type": "gps",
         "service_type_label": "GPS", "plan": "Rastreo"},
    ], "count": 3})
    ctx.fake.json_responses["/v1/billing/summary"] = (200, {
        "currency": "MXN", "total_due": 500.0, "overdue_amount": 500.0, "open_count": 1,
        "upcoming": [{"id": 9, "number": "INV/1", "due_date": "2026-07-01", "amount_due": 500.0}]})
    r = ctx.client.get("/v1/dashboard", headers=_h(tok))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["data"]["peace_of_mind"]["status"] == "atencion"
    assert d["data"]["services"]["suspended"] == 1
    types = {a["type"] for a in d["data"]["next_actions"]}
    assert {"payment_overdue", "service_suspended", "contract_pending_signature", "invoice_due"} <= types
    # severidad alta primero
    assert d["data"]["next_actions"][0]["severity"] == "high"
    assert d["meta"]["last_refresh"] and d["meta"]["cache_ttl_sec"] == 30


def test_dashboard_peace_when_clean(ctx):
    tok = _login(ctx)
    ctx.fake.json_responses["/v1/services"] = (200, {"items": [
        {"id": 1, "status": "active", "reference": "S", "service_type": "alarm",
         "service_type_label": "Alarma", "plan": "P"}], "count": 1})
    ctx.fake.json_responses["/v1/billing/summary"] = (200, {
        "currency": "MXN", "total_due": 0, "overdue_amount": 0, "upcoming": []})
    d = ctx.client.get("/v1/dashboard", headers=_h(tok)).json()
    assert d["data"]["peace_of_mind"]["status"] == "tranquilo"
    assert d["data"]["next_actions"] == []


def test_dashboard_cache_serves_stale_within_ttl(ctx):
    tok = _login(ctx)
    ctx.fake.json_responses["/v1/services"] = (200, {"items": [], "count": 0})
    ctx.fake.json_responses["/v1/billing/summary"] = (200, {"currency": "MXN", "total_due": 0, "overdue_amount": 0, "upcoming": []})
    r1 = ctx.client.get("/v1/dashboard", headers=_h(tok)).json()
    # Odoo cambia, pero dentro del TTL el dashboard debe servir lo cacheado
    ctx.fake.json_responses["/v1/services"] = (200, {"items": [{"id": 1, "status": "active"}], "count": 1})
    r2 = ctx.client.get("/v1/dashboard", headers=_h(tok)).json()
    assert r2["data"]["services"]["total"] == 0
    assert r1["meta"]["last_refresh"] == r2["meta"]["last_refresh"]


def test_invoice_pdf_proxy(ctx):
    tok = _login(ctx)
    ctx.fake.raw_responses["/v1/billing/invoices/5/pdf"] = (200, b"%PDF-1.4 fake", "application/pdf", 'inline; filename="INV-5.pdf"')
    r = ctx.client.get("/v1/billing/invoices/5/pdf", headers=_h(tok))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF")


def test_session_expired_maps_to_401(ctx):
    tok = _login(ctx)
    ctx.fake.json_responses["/v1/services"] = (303, None)
    assert ctx.client.get("/v1/services", headers=_h(tok)).status_code == 401


def test_invoice_not_found_maps_404(ctx):
    tok = _login(ctx)
    # sin canned -> FakeOdooClient devuelve 404
    assert ctx.client.get("/v1/billing/invoices/999", headers=_h(tok)).status_code == 404

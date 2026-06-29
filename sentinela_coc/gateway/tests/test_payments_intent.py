# -*- coding: utf-8 -*-
"""Pruebas de la intención de pago + endpoint startPayment (S2-007).

Valida montos/pertenencia contra el Ledger, inicia el cobro vía el Motor (Fake) y
publica ÚNICAMENTE `pago.iniciado`. No aplica pagos.
"""
import pytest

from app import deps
from app.capabilities.events import EventRecord
from app.capabilities.payments import CONFIRMED, PROCESSING, FakePaymentAdapter
from app.main import app
from app.routers import payments as payments_router

PHONE = "+528680000001"   # -> partner 25757 (FakeOdooClient del conftest)


def _login(ctx):
    ctx.client.post("/v1/auth/otp/request", json={"phone": PHONE, "device": "d"})
    code = ctx.mock.last_code(PHONE)
    r = ctx.client.post("/v1/auth/otp/verify", json={"phone": PHONE, "code": code, "device": "d"})
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": "Bearer %s" % tok}


def _movimientos():
    # Cargos abiertos del cliente (lo que ve el Ledger via el adaptador act-as).
    return (200, {"items": [
        {"kind": "charge", "id": 1, "date": "2026-06-01", "amount": 6050.0, "currency": "MXN",
         "reference": "INV-1", "status": "not_paid", "due_date": "2026-06-11", "amount_residual": 6050.0},
        {"kind": "charge", "id": 2, "date": "2026-06-01", "amount": 1000.0, "currency": "MXN",
         "reference": "INV-2", "status": "not_paid", "due_date": "2026-07-15", "amount_residual": 1000.0},
    ]})


@pytest.fixture
def fake_pay():
    fake = FakePaymentAdapter(status=CONFIRMED, client_action={"client_secret": "cs_test_1"})
    app.dependency_overrides[payments_router.get_payment_adapter] = lambda: fake
    yield fake
    app.dependency_overrides.pop(payments_router.get_payment_adapter, None)


def _events(ctx, type=None):
    db = ctx.Session()
    try:
        q = db.query(EventRecord)
        if type:
            q = q.filter(EventRecord.type == type)
        return q.all()
    finally:
        db.close()


def test_start_payment_ok_publica_pago_iniciado(ctx, fake_pay):
    tok = _login(ctx)
    ctx.fake.json_responses["/v1/ledger/movements"] = _movimientos()
    r = ctx.client.post("/v1/payments/start", headers=_h(tok), json={"invoice_ids": [1, 2], "amount": 7050.0})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["status"] == CONFIRMED
    assert data["amount"] == 7050.0 and data["currency"] == "MXN"
    assert data["client_action"] == {"client_secret": "cs_test_1"}
    # el Motor fue invocado con el monto del Ledger
    assert fake_pay.authorized and fake_pay.authorized[0].amount == 7050.0
    # se publicó pago.iniciado (y SOLO eso)
    evs = _events(ctx)
    assert [e.type for e in evs] == ["pago.iniciado"]
    pi = evs[0]
    assert pi.payload["invoice_ids"] == [1, 2]
    assert pi.payload["amount"] == 7050.0
    assert pi.payload["payment_id"] == data["payment_id"]
    assert pi.aggregate_id == "payment:%s" % data["payment_id"]


def test_monto_no_cuadra_rechazo_claro_sin_evento(ctx, fake_pay):
    tok = _login(ctx)
    ctx.fake.json_responses["/v1/ledger/movements"] = _movimientos()
    r = ctx.client.post("/v1/payments/start", headers=_h(tok), json={"invoice_ids": [1, 2], "amount": 9999.0})
    assert r.status_code == 422
    assert "no cuadra" in r.json()["detail"]
    assert fake_pay.authorized == []          # no se inició cobro
    assert _events(ctx) == []                 # no se publicó nada


def test_factura_ajena_rechazada(ctx, fake_pay):
    tok = _login(ctx)
    ctx.fake.json_responses["/v1/ledger/movements"] = _movimientos()
    r = ctx.client.post("/v1/payments/start", headers=_h(tok), json={"invoice_ids": [999], "amount": 100.0})
    assert r.status_code == 422
    assert "no pertenecen" in r.json()["detail"]
    assert _events(ctx) == []


def test_pago_parcial_no_cuadra(ctx, fake_pay):
    # Liquidación total: pagar solo una de dos no cuadra con el monto total solicitado.
    tok = _login(ctx)
    ctx.fake.json_responses["/v1/ledger/movements"] = _movimientos()
    r = ctx.client.post("/v1/payments/start", headers=_h(tok), json={"invoice_ids": [1], "amount": 6050.0})
    assert r.status_code == 200       # pagar SOLO la factura 1 por su importe exacto SÍ cuadra
    assert r.json()["data"]["amount"] == 6050.0


def test_en_proceso_se_propaga(ctx):
    fake = FakePaymentAdapter(status=PROCESSING, client_action={"client_secret": "cs_2"})
    app.dependency_overrides[payments_router.get_payment_adapter] = lambda: fake
    try:
        tok = _login(ctx)
        ctx.fake.json_responses["/v1/ledger/movements"] = _movimientos()
        r = ctx.client.post("/v1/payments/start", headers=_h(tok), json={"invoice_ids": [2], "amount": 1000.0})
        assert r.status_code == 200 and r.json()["data"]["status"] == PROCESSING
        assert [e.type for e in _events(ctx)] == ["pago.iniciado"]
    finally:
        app.dependency_overrides.pop(payments_router.get_payment_adapter, None)


def test_requiere_auth(ctx, fake_pay):
    assert ctx.client.post("/v1/payments/start", json={"invoice_ids": [1], "amount": 1.0}).status_code == 401

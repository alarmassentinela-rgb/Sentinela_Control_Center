# -*- coding: utf-8 -*-
"""Pruebas del Estado de Cuenta del Ledger (S2-004).

Cálculo correcto de saldo/vencido/por vencer a partir de los hechos del adaptador,
por servicio; el cálculo vive SOLO en el Ledger. Incluye prueba del endpoint
/v1/ledger/statement (con sesión real, Odoo fake).
"""
from datetime import date

import pytest

from app.capabilities.ledger import FakeAccountingAdapter, Ledger, Movement, CHARGE, NOTE, PAYMENT

HOY = date(2026, 6, 29)


def charge(id, residual, due, service_id=None):
    return Movement(id=id, kind=CHARGE, date="2026-06-01", amount=abs(residual), currency="MXN",
                    reference="INV-%s" % id, status="not_paid", service_id=service_id,
                    due_date=due, amount_residual=residual)


def payment(id, amount):
    return Movement(id=id, kind=PAYMENT, date="2026-06-20", amount=amount, currency="MXN",
                    reference="PAY-%s" % id, status="posted")   # sin residual


def note(id, residual, due, service_id=None):
    return Movement(id=id, kind=NOTE, date="2026-06-10", amount=abs(residual), currency="MXN",
                    reference="NC-%s" % id, status="not_paid", service_id=service_id,
                    due_date=due, amount_residual=residual)


def test_saldo_vencido_por_vencer():
    led = Ledger(FakeAccountingAdapter([
        charge(1, 6050.0, "2026-06-11"),   # vencido (antes de hoy)
        charge(2, 1000.0, "2026-07-15"),   # por vencer
        payment(3, 500.0),                 # informativo: no afecta el balance
    ]))
    st = led.account_statement(today=HOY)
    assert st.balance == 7050.0
    assert st.overdue == 6050.0
    assert st.upcoming == 1000.0
    assert st.currency == "MXN"


def test_nota_de_credito_reduce_saldo():
    led = Ledger(FakeAccountingAdapter([
        charge(1, 1000.0, "2026-07-15"),
        note(2, -300.0, "2026-07-15"),     # residual negativo -> reduce
    ]))
    st = led.account_statement(today=HOY)
    assert st.balance == 700.0
    assert st.upcoming == 700.0
    assert st.overdue == 0.0


def test_cargo_pagado_residual_cero_no_suma():
    led = Ledger(FakeAccountingAdapter([charge(1, 0.0, "2026-06-11"), charge(2, 200.0, "2026-06-11")]))
    st = led.account_statement(today=HOY)
    assert st.balance == 200.0 and st.overdue == 200.0


def test_por_servicio_filtra():
    led = Ledger(FakeAccountingAdapter([
        charge(1, 100.0, "2026-06-11", service_id=10),
        charge(2, 999.0, "2026-06-11", service_id=20),
    ]))
    st = led.account_statement(today=HOY, service_id=10)
    assert st.balance == 100.0 and st.overdue == 100.0


def test_sin_movimientos():
    st = Ledger(FakeAccountingAdapter([])).account_statement(today=HOY)
    assert st.balance == 0.0 and st.overdue == 0.0 and st.upcoming == 0.0 and st.currency == "MXN"


def test_cargo_sin_vencimiento_cuenta_al_saldo_no_a_buckets():
    led = Ledger(FakeAccountingAdapter([charge(1, 500.0, None)]))
    st = led.account_statement(today=HOY)
    assert st.balance == 500.0 and st.overdue == 0.0 and st.upcoming == 0.0


# ---- endpoint /v1/ledger/statement (sesión real, Odoo fake) ----
PHONE = "+528680000001"   # -> partner 25757 (FakeOdooClient del conftest)


def _login(ctx):
    ctx.client.post("/v1/auth/otp/request", json={"phone": PHONE, "device": "d"})
    code = ctx.mock.last_code(PHONE)
    r = ctx.client.post("/v1/auth/otp/verify", json={"phone": PHONE, "code": code, "device": "d"})
    return r.json()["access_token"]


def test_endpoint_estado_cuenta(ctx):
    tok = _login(ctx)
    ctx.fake.json_responses["/v1/ledger/movements"] = (200, {"items": [
        {"kind": "charge", "id": 1, "date": "2026-06-01", "amount": 6050.0, "currency": "MXN",
         "reference": "INV-1", "status": "not_paid", "due_date": "2020-01-01", "amount_residual": 6050.0},
        {"kind": "charge", "id": 2, "date": "2026-06-01", "amount": 1000.0, "currency": "MXN",
         "reference": "INV-2", "status": "not_paid", "due_date": "2099-01-01", "amount_residual": 1000.0},
        {"kind": "payment", "id": 3, "date": "2026-06-20", "amount": 500.0, "currency": "MXN", "reference": "PAY-3"},
    ]})
    r = ctx.client.get("/v1/ledger/statement", headers={"Authorization": "Bearer %s" % tok})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"] == {"currency": "MXN", "balance": 7050.0, "overdue": 6050.0, "upcoming": 1000.0}
    assert body["meta"]["server_time"] and body["meta"]["request_id"]


def test_endpoint_requiere_auth(ctx):
    assert ctx.client.get("/v1/ledger/statement").status_code == 401


def test_endpoint_sesion_expirada_401(ctx):
    tok = _login(ctx)
    ctx.fake.json_responses["/v1/ledger/movements"] = (303, None)
    assert ctx.client.get("/v1/ledger/statement", headers={"Authorization": "Bearer %s" % tok}).status_code == 401

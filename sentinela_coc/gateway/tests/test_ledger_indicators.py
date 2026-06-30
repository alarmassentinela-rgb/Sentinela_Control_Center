# -*- coding: utf-8 -*-
"""Pruebas de los indicadores MVP del Ledger (S2-013).

EXACTAMENTE 3 indicadores desde el Ledger: cobrado hoy, cartera vencida, pagos
pendientes. Sin Dashboard Engine.
"""
from datetime import date

from app.capabilities.ledger import FakeAccountingAdapter, Indicators, LedgerIndicators, Movement, CHARGE, PAYMENT

HOY = date(2026, 6, 30)


def charge(id, residual, due):
    return Movement(id=id, kind=CHARGE, date="2026-06-01", amount=abs(residual), currency="MXN",
                    reference="INV-%s" % id, status="not_paid", due_date=due, amount_residual=residual)


def payment(id, amount, d):
    return Movement(id=id, kind=PAYMENT, date=d, amount=amount, currency="MXN", reference="PAY-%s" % id)


def test_los_tres_indicadores():
    ind = LedgerIndicators(FakeAccountingAdapter([
        payment(1, 500.0, "2026-06-30"),    # cobrado HOY
        payment(2, 999.0, "2026-06-29"),    # ayer -> NO cuenta para cobrado hoy
        charge(3, 6050.0, "2026-06-11"),    # vencido
        charge(4, 1000.0, "2026-07-15"),    # por vencer (pendiente, no vencido)
    ])).compute(today=HOY)
    assert isinstance(ind, Indicators)
    assert ind.collected_today == 500.0
    assert ind.overdue_portfolio == 6050.0
    assert ind.pending_payments == 7050.0   # 6050 + 1000 (saldo abierto total)
    assert ind.currency == "MXN"


def test_sin_movimientos_indicadores_en_cero():
    ind = LedgerIndicators(FakeAccountingAdapter([])).compute(today=HOY)
    assert ind.collected_today == 0.0 and ind.overdue_portfolio == 0.0 and ind.pending_payments == 0.0


def test_cobrado_hoy_solo_pagos_de_hoy():
    ind = LedgerIndicators(FakeAccountingAdapter([
        payment(1, 100.0, "2026-06-30"), payment(2, 50.0, "2026-06-30"),
        payment(3, 999.0, "2026-06-01"),
    ])).compute(today=HOY)
    assert ind.collected_today == 150.0


def test_solo_expone_tres_indicadores():
    ind = LedgerIndicators(FakeAccountingAdapter([])).compute(today=HOY)
    assert set(ind.as_dict()) == {"currency", "collected_today", "overdue_portfolio", "pending_payments"}


# ---- endpoint /v1/ledger/indicators (sesión real, Odoo fake) ----
PHONE = "+528680000001"


def _login(ctx):
    ctx.client.post("/v1/auth/otp/request", json={"phone": PHONE, "device": "d"})
    code = ctx.mock.last_code(PHONE)
    return ctx.client.post("/v1/auth/otp/verify", json={"phone": PHONE, "code": code, "device": "d"}).json()["access_token"]


def test_endpoint_indicadores(ctx):
    tok = _login(ctx)
    ctx.fake.json_responses["/v1/ledger/movements"] = (200, {"items": [
        {"kind": "payment", "id": 1, "date": "2099-01-01", "amount": 0.0, "currency": "MXN", "reference": "P"},
        {"kind": "charge", "id": 2, "date": "2026-06-01", "amount": 6050.0, "currency": "MXN",
         "reference": "INV-2", "due_date": "2020-01-01", "amount_residual": 6050.0},
    ]})
    r = ctx.client.get("/v1/ledger/indicators", headers={"Authorization": "Bearer %s" % tok})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert set(d) == {"currency", "collected_today", "overdue_portfolio", "pending_payments"}
    assert d["overdue_portfolio"] == 6050.0 and d["pending_payments"] == 6050.0


def test_endpoint_requiere_auth(ctx):
    assert ctx.client.get("/v1/ledger/indicators").status_code == 401

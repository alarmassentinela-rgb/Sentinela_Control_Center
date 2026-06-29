# -*- coding: utf-8 -*-
"""Pruebas del adaptador contable de lectura (S2-003).

Verifican: el adaptador devuelve movimientos NORMALIZADOS de un cliente; filtra por
servicio; el adaptador Odoo encapsula a Odoo (normaliza la respuesta act-as) y el
Ledger podrá depender SOLO de la interfaz AccountingAdapter (no de Odoo).
"""
import pytest

from app.capabilities.ledger import (
    AccountingAdapter,
    AccountingUnavailable,
    FakeAccountingAdapter,
    Movement,
    OdooAccountingAdapter,
    CHARGE,
    PAYMENT,
    NOTE,
)


def _mov(id, kind, amount, service_id=None):
    return Movement(id=id, kind=kind, date="2026-06-11", amount=amount,
                    currency="MXN", reference="REF-%s" % id, status="posted",
                    service_id=service_id)


# ---- Fake adapter: contrato normalizado + filtro por servicio ----
def test_fake_devuelve_movimientos_del_cliente():
    adapter = FakeAccountingAdapter([
        _mov(1, CHARGE, 6050.0), _mov(2, PAYMENT, 6050.0), _mov(3, NOTE, 100.0),
    ])
    movs = adapter.movements()
    assert [m.kind for m in movs] == [CHARGE, PAYMENT, NOTE]
    assert all(isinstance(m, Movement) for m in movs)
    assert movs[0].amount == 6050.0 and movs[0].currency == "MXN"


def test_fake_filtra_por_servicio():
    adapter = FakeAccountingAdapter([
        _mov(1, CHARGE, 100.0, service_id=10),
        _mov(2, CHARGE, 200.0, service_id=20),
        _mov(3, PAYMENT, 50.0, service_id=10),
    ])
    s10 = adapter.movements(service_id=10)
    assert [m.id for m in s10] == [1, 3]
    assert adapter.movements(service_id=99) == []


def test_fake_es_accounting_adapter_sin_odoo():
    # El Ledger (S2-004) dependerá de esta interfaz, no de Odoo.
    adapter = FakeAccountingAdapter([])
    assert isinstance(adapter, AccountingAdapter)


# ---- Odoo adapter: normaliza la respuesta act-as; encapsula a Odoo ----
class _StubOdoo:
    """Cliente Odoo mínimo: responde a get_json_as como el HttpOdooClient real."""
    def __init__(self, status, body):
        self.status, self.body = status, body
        self.calls = []

    def get_json_as(self, sid, path, params=None):
        self.calls.append((sid, path, params))
        return self.status, self.body


def test_odoo_adapter_normaliza_la_respuesta():
    raw = {"items": [
        {"kind": "charge", "id": 451, "date": "2026-06-11", "amount": 6050.0,
         "currency": "MXN", "reference": "INV/2026/00184", "status": "not_paid", "service_id": None},
        {"kind": "payment", "id": 12, "date": "2026-06-20", "amount": 6050, "reference": "PAY/1"},
    ]}
    odoo = _StubOdoo(200, raw)
    adapter = OdooAccountingAdapter(odoo, "sess-abc")
    movs = adapter.movements()
    assert odoo.calls == [("sess-abc", "/v1/ledger/movements", {})]
    assert [m.kind for m in movs] == ["charge", "payment"]
    assert movs[0].reference == "INV/2026/00184" and movs[0].id == 451
    assert movs[1].amount == 6050.0 and movs[1].currency == "MXN"   # defaults aplicados


def test_odoo_adapter_pasa_filtro_de_servicio():
    odoo = _StubOdoo(200, {"items": []})
    OdooAccountingAdapter(odoo, "s1").movements(service_id=7)
    assert odoo.calls == [("s1", "/v1/ledger/movements", {"service_id": 7})]


def test_odoo_adapter_error_levanta_unavailable():
    odoo = _StubOdoo(502, None)
    with pytest.raises(AccountingUnavailable):
        OdooAccountingAdapter(odoo, "s1").movements()

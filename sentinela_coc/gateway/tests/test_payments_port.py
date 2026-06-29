# -*- coding: utf-8 -*-
"""Pruebas del puerto PaymentAdapter + Motor de Pago (S2-005).

El Motor autoriza una intención con el Fake; maneja confirmado/en proceso/rechazado;
valida la intención; y NO referencia a ningún proveedor (sin importar Stripe).
"""
import ast
import inspect

import pytest

import app.capabilities.payments.service as motor_module
from app.capabilities.payments import (
    CONFIRMED,
    PROCESSING,
    REJECTED,
    FakePaymentAdapter,
    InvalidPaymentIntent,
    PaymentEngine,
    PaymentIntent,
)


def _intent(amount=6050.0, key="idem-1"):
    return PaymentIntent(amount=amount, currency="MXN", reference="INV-1,INV-2",
                         idempotency_key=key, metadata={"partner_id": 25043})


def test_motor_autoriza_con_el_fake():
    fake = FakePaymentAdapter(status=CONFIRMED)
    res = PaymentEngine(fake).authorize(_intent())
    assert res.status == CONFIRMED
    assert res.provider_ref == "fake-pay-1"
    assert fake.authorized and fake.authorized[0].amount == 6050.0


def test_motor_propaga_en_proceso_y_rechazado():
    res_proc = PaymentEngine(FakePaymentAdapter(status=PROCESSING)).authorize(_intent())
    assert res_proc.status == PROCESSING

    fake_rej = FakePaymentAdapter(status=REJECTED, reason="card_declined")
    res_rej = PaymentEngine(fake_rej).authorize(_intent())
    assert res_rej.status == REJECTED and res_rej.reason == "card_declined"


def test_motor_rechaza_monto_no_positivo_sin_llamar_al_adaptador():
    fake = FakePaymentAdapter()
    with pytest.raises(InvalidPaymentIntent):
        PaymentEngine(fake).authorize(_intent(amount=0))
    assert fake.authorized == []     # no se tocó al adaptador


def test_motor_exige_idempotency_key():
    fake = FakePaymentAdapter()
    with pytest.raises(InvalidPaymentIntent):
        PaymentEngine(fake).authorize(_intent(key=""))
    assert fake.authorized == []


def test_motor_confirma_via_adaptador():
    fake = FakePaymentAdapter(status=CONFIRMED)
    res = PaymentEngine(fake).confirm("fake-pay-9")
    assert res.status == CONFIRMED and res.provider_ref == "fake-pay-9"
    assert fake.confirmed == ["fake-pay-9"]


def test_refund_es_stub():
    fake = FakePaymentAdapter()
    res = fake.refund("fake-pay-1")
    assert res.status == PROCESSING
    assert fake.refunded == [("fake-pay-1", None)]


def _imports(module) -> set:
    """Nombres de módulos importados (raíz), vía AST — ignora docstrings/comentarios."""
    tree = ast.parse(inspect.getsource(module))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_motor_no_importa_a_stripe_ni_a_proveedor():
    """Criterio de aceptación: ninguna importación de Stripe en el Motor (ni en el puerto).
    Se valida por IMPORTS reales (AST), no por la palabra en los docstrings que explican la regla."""
    import app.capabilities.payments.port as port_module
    assert "stripe" not in _imports(motor_module)
    assert "stripe" not in _imports(port_module)
    # el Motor solo conoce el puerto (sin importar adaptadores concretos)
    assert "fake_adapter" not in _imports(motor_module)

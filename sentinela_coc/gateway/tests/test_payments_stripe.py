# -*- coding: utf-8 -*-
"""Pruebas del adaptador Stripe (S2-006).

Autoriza un cobro (cliente Stripe FAKE inyectado — sin red ni paquete stripe),
mapea el estado al vocabulario de negocio, usa la clave por CONFIGURACIÓN (no
hardcode) y envía centavos/idempotency_key. Confirma y maneja error→rechazado.
"""
import inspect
from types import SimpleNamespace

import pytest

from app.capabilities.payments import CONFIRMED, PROCESSING, REJECTED, PaymentAdapter, PaymentIntent
import app.capabilities.payments.stripe_adapter as stripe_mod
from app.capabilities.payments.stripe_adapter import StripePaymentAdapter


class _FakeStripe:
    """Imita stripe.PaymentIntent.create/retrieve, registra llamadas; opcional excepción."""
    def __init__(self, status="requires_payment_method", pid="pi_test_1",
                 client_secret="cs_test_1", raise_exc=None):
        calls = self.calls = []
        self._status, self._pid, self._cs, self._exc = status, pid, client_secret, raise_exc

        class PaymentIntent:
            @staticmethod
            def create(**kw):
                calls.append(("create", kw))
                if self._exc:
                    raise self._exc
                return SimpleNamespace(status=self._status, id=self._pid, client_secret=self._cs)

            @staticmethod
            def retrieve(ref, **kw):
                calls.append(("retrieve", ref, kw))
                return SimpleNamespace(status=self._status, id=ref, client_secret=self._cs)

        self.PaymentIntent = PaymentIntent


def _intent():
    return PaymentIntent(amount=6050.0, currency="MXN", reference="INV-1",
                         idempotency_key="idem-xyz", metadata={"partner_id": 25043})


def test_es_payment_adapter():
    assert isinstance(StripePaymentAdapter("sk_test_123", client=_FakeStripe()), PaymentAdapter)


def test_requiere_clave():
    with pytest.raises(ValueError):
        StripePaymentAdapter("", client=_FakeStripe())


@pytest.mark.parametrize("stripe_status,esperado", [
    ("succeeded", CONFIRMED),
    ("processing", PROCESSING),
    ("requires_payment_method", PROCESSING),
    ("requires_action", PROCESSING),
    ("canceled", REJECTED),
])
def test_authorize_mapea_estado(stripe_status, esperado):
    adapter = StripePaymentAdapter("sk_test_123", client=_FakeStripe(status=stripe_status))
    res = adapter.authorize(_intent())
    assert res.status == esperado
    assert res.provider_ref == "pi_test_1"
    assert res.client_action == {"client_secret": "cs_test_1"}


def test_authorize_envia_centavos_idempotency_y_clave_de_config():
    fake = _FakeStripe()
    StripePaymentAdapter("sk_test_ABC", client=fake).authorize(_intent())
    _, kw = fake.calls[0]
    assert kw["amount"] == 605000              # 6050.00 -> centavos
    assert kw["currency"] == "mxn"
    assert kw["idempotency_key"] == "idem-xyz"  # provista por el caso de uso, solo propagada
    assert kw["api_key"] == "sk_test_ABC"       # clave por configuración (no hardcode)
    assert kw["metadata"]["reference"] == "INV-1"


def test_authorize_error_mapea_rejected():
    fake = _FakeStripe(raise_exc=Exception("card_declined"))
    res = StripePaymentAdapter("sk_test_123", client=fake).authorize(_intent())
    assert res.status == REJECTED and "card_declined" in (res.reason or "")


def test_confirm_mapea_estado():
    fake = _FakeStripe(status="succeeded")
    res = StripePaymentAdapter("sk_test_123", client=fake).confirm("pi_abc")
    assert res.status == CONFIRMED and res.provider_ref == "pi_abc"
    assert fake.calls[0][0] == "retrieve"


def test_refund_no_implementado():
    with pytest.raises(NotImplementedError):
        StripePaymentAdapter("sk_test_123", client=_FakeStripe()).refund("pi_abc")


def test_sin_clave_hardcodeada_en_el_adaptador():
    """No debe haber claves Stripe embebidas (sk_test_/sk_live_/pk_/whsec_) en el código."""
    src = inspect.getsource(stripe_mod)
    for prefijo in ("sk_test_", "sk_live_", "pk_test_", "pk_live_", "whsec_"):
        assert prefijo not in src

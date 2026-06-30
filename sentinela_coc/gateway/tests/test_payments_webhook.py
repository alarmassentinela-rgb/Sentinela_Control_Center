# -*- coding: utf-8 -*-
"""Pruebas del webhook de confirmación de pago (S2-008).

Firma verificada (en el adaptador), idempotencia (dedupe por id del evento del
proveedor), publica ÚNICAMENTE pago.confirmado/pago.rechazado, maneja en proceso.
No aplica el pago contable.
"""
import pytest

from app import deps
from app.capabilities.events import EventRecord
from app.capabilities.payments.stripe_adapter import StripePaymentAdapter
from app.main import app
from app.routers import payments as payments_router


class _FakeStripe:
    """stripe.Webhook.construct_event: devuelve un evento o lanza (firma inválida)."""
    def __init__(self, event=None, raise_exc=None):
        ev, exc = event, raise_exc

        class Webhook:
            @staticmethod
            def construct_event(payload, signature, secret):
                if exc:
                    raise exc
                return ev

        self.Webhook = Webhook


def _evt(etype, pid="pi_123", evid="evt_1", extra=None):
    obj = {"id": pid}
    if extra:
        obj.update(extra)
    return {"id": evid, "type": etype, "data": {"object": obj}}


def _use_stripe(fake):
    adapter = StripePaymentAdapter("sk_test_x", webhook_secret="whsec_x", client=fake)
    app.dependency_overrides[payments_router.get_payment_adapter] = lambda: adapter


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.pop(payments_router.get_payment_adapter, None)


def _post(ctx, sig="t=1,v1=abc"):
    return ctx.client.post("/v1/payments/webhook", content=b'{"raw":"body"}',
                           headers={"stripe-signature": sig})


def _events(ctx, type=None):
    db = ctx.Session()
    try:
        q = db.query(EventRecord)
        if type:
            q = q.filter(EventRecord.type == type)
        return q.all()
    finally:
        db.close()


def test_confirmado_publica_pago_confirmado(ctx):
    _use_stripe(_FakeStripe(event=_evt("payment_intent.succeeded", pid="pi_9", evid="evt_A")))
    r = _post(ctx)
    assert r.status_code == 200 and r.json()["published"] is True and r.json()["type"] == "pago.confirmado"
    evs = _events(ctx)
    assert [e.type for e in evs] == ["pago.confirmado"]
    assert evs[0].payload["payment_id"] == "pi_9"
    assert evs[0].aggregate_id == "payment:pi_9"


def test_rechazado_publica_pago_rechazado(ctx):
    _use_stripe(_FakeStripe(event=_evt("payment_intent.payment_failed", pid="pi_3",
                                       extra={"last_payment_error": {"message": "card_declined"}})))
    r = _post(ctx)
    assert r.json()["type"] == "pago.rechazado"
    ev = _events(ctx, "pago.rechazado")[0]
    assert ev.payload["reason"] == "card_declined"


def test_en_proceso_no_publica(ctx):
    _use_stripe(_FakeStripe(event=_evt("payment_intent.processing")))
    r = _post(ctx)
    assert r.status_code == 200 and r.json()["published"] is False
    assert _events(ctx) == []


def test_evento_no_relevante_se_ignora(ctx):
    _use_stripe(_FakeStripe(event=_evt("charge.updated")))
    assert _post(ctx).json()["published"] is False
    assert _events(ctx) == []


def test_firma_invalida_400_sin_evento(ctx):
    _use_stripe(_FakeStripe(raise_exc=Exception("bad signature")))
    r = _post(ctx)
    assert r.status_code == 400 and r.json()["detail"] == "invalid_signature"
    assert _events(ctx) == []


def test_idempotente_webhook_duplicado_publica_una_vez(ctx):
    _use_stripe(_FakeStripe(event=_evt("payment_intent.succeeded", pid="pi_7", evid="evt_DUP")))
    r1 = _post(ctx)
    r2 = _post(ctx)   # mismo evt_DUP
    assert r1.json()["published"] is True
    assert r2.json()["published"] is False        # no se publicó de nuevo
    assert len(_events(ctx, "pago.confirmado")) == 1   # una sola fila

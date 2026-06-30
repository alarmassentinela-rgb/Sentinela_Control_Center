# -*- coding: utf-8 -*-
"""Pruebas de la aplicación de pago (S2-009).

Consume `pago.confirmado` (correlacionado con `pago.iniciado`), aplica vía el puerto
contable, publica `factura.pagada` por factura liquidada. Idempotente (una sola vez)
y conciliado (no duplica con depósito ya pagado).
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.capabilities.events import EventStore
from app.capabilities.events.catalog import CatalogedEventStore
from app.capabilities.payments.application import (
    AccountingPaymentPort,
    FakeAccountingPayments,
    PaymentApplication,
)

PID = "pi_1"


@pytest.fixture
def store():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, future=True)()
    try:
        yield CatalogedEventStore(EventStore(db))
    finally:
        db.close()


def _iniciado(store, invoice_ids, amount, payment_id=PID, partner_id=25043):
    store.append(event_id="ini-%s" % payment_id, type="pago.iniciado",
                 aggregate_id="payment:%s" % payment_id,
                 payload={"payment_id": payment_id, "partner_id": partner_id,
                          "invoice_ids": invoice_ids, "amount": amount, "currency": "MXN",
                          "status": "processing"})


def _confirmado(store, payment_id=PID):
    store.append(event_id="con-%s" % payment_id, type="pago.confirmado",
                 aggregate_id="payment:%s" % payment_id,
                 payload={"payment_id": payment_id, "status": "confirmed"})


def _facturas_pagadas(store):
    return sorted(e.payload["invoice_id"] for e in store.read(type="factura.pagada"))


def test_aplica_y_publica_factura_pagada(store):
    _iniciado(store, [1, 2], 7050.0)
    _confirmado(store)
    write = FakeAccountingPayments(paid=[1, 2])
    out = PaymentApplication(write, store).apply_confirmed_payment(PID)
    assert out.applied is True
    assert _facturas_pagadas(store) == [1, 2]
    # el puerto recibió el pago con su external_ref
    assert write.calls and write.calls[0][4] == PID


def test_solo_actua_sobre_pago_confirmado(store):
    _iniciado(store, [1], 100.0)   # iniciado pero NO confirmado
    write = FakeAccountingPayments(paid=[1])
    out = PaymentApplication(write, store).apply_confirmed_payment(PID)
    assert out.applied is False and out.skipped_reason == "no_confirmado"
    assert write.calls == [] and _facturas_pagadas(store) == []


def test_idempotente_se_aplica_una_sola_vez(store):
    _iniciado(store, [1, 2], 7050.0)
    _confirmado(store)
    write = FakeAccountingPayments(paid=[1, 2])
    app = PaymentApplication(write, store)
    app.apply_confirmed_payment(PID)
    out2 = app.apply_confirmed_payment(PID)   # reintento
    assert out2.applied is False and out2.skipped_reason == "ya_aplicado"
    assert len(write.calls) == 1                       # el contable se tocó una sola vez
    assert _facturas_pagadas(store) == [1, 2]          # sin duplicar facturas


def test_conciliacion_no_duplica_con_deposito_ya_pagado(store):
    _iniciado(store, [1, 2], 7050.0)
    _confirmado(store)
    # factura 2 ya pagada por depósito (OXXO/banco): el puerto solo liquida la 1
    write = FakeAccountingPayments(paid=[1], already_paid=[2])
    PaymentApplication(write, store).apply_confirmed_payment(PID)
    assert _facturas_pagadas(store) == [1]             # NO se emite factura.pagada para la 2


def test_sin_intencion_no_aplica(store):
    _confirmado(store)   # confirmado sin pago.iniciado
    write = FakeAccountingPayments(paid=[1])
    out = PaymentApplication(write, store).apply_confirmed_payment(PID)
    assert out.applied is False and out.skipped_reason == "sin_intencion"
    assert write.calls == []


def test_fake_es_accounting_payment_port():
    assert isinstance(FakeAccountingPayments(), AccountingPaymentPort)

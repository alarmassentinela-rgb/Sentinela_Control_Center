# -*- coding: utf-8 -*-
"""Pruebas de la notificación de confirmación de pago (S2-012).

El consumidor reacciona a `pago.confirmado`, notifica por el canal (puerto) una sola
vez, tomando el detalle del `pago.iniciado`. Desacoplado del flujo de pagos.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.capabilities.events import EventStore
from app.capabilities.events.catalog import CatalogedEventStore
from app.capabilities.notifications import (
    FakeNotificationChannel,
    NotificationPort,
    NotificationsConsumer,
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


def _iniciado(store, partner_id=25043, amount=7050.0):
    store.append(event_id="ini-%s" % PID, type="pago.iniciado", aggregate_id="payment:%s" % PID,
                 payload={"payment_id": PID, "partner_id": partner_id, "invoice_ids": [1, 2],
                          "amount": amount, "currency": "MXN", "status": "processing"})


def _confirmado(store):
    store.append(event_id="con-%s" % PID, type="pago.confirmado", aggregate_id="payment:%s" % PID,
                 payload={"payment_id": PID, "status": "confirmed"})


def test_notifica_al_confirmar(store):
    _iniciado(store)
    _confirmado(store)
    ch = FakeNotificationChannel()
    out = NotificationsConsumer(ch, store).on_payment_confirmed(PID)
    assert out.notified is True and out.partner_id == 25043
    assert ch.sent == [(25043, PID, 7050.0, "MXN")]   # una sola notificación, datos del pago.iniciado


def test_requiere_pago_confirmado(store):
    _iniciado(store)   # sin pago.confirmado
    ch = FakeNotificationChannel()
    out = NotificationsConsumer(ch, store).on_payment_confirmed(PID)
    assert out.notified is False and out.reason == "no_confirmado"
    assert ch.sent == []


def test_una_sola_notificacion_por_pago(store):
    _iniciado(store)
    _confirmado(store)
    ch = FakeNotificationChannel()
    NotificationsConsumer(ch, store).on_payment_confirmed(PID)
    assert len(ch.sent) == 1


def test_solo_reacciona_al_evento_sin_intencion(store):
    # confirmado sin pago.iniciado: notifica con datos mínimos (partner None), pero reacciona al evento.
    _confirmado(store)
    ch = FakeNotificationChannel()
    out = NotificationsConsumer(ch, store).on_payment_confirmed(PID)
    assert out.notified is True
    assert ch.sent == [(None, PID, 0.0, "MXN")]


def test_fake_es_notification_port():
    assert isinstance(FakeNotificationChannel(), NotificationPort)

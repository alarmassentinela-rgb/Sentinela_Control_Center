# -*- coding: utf-8 -*-
"""Aceptación E2E de la vertical Cobranza (S2-015).

Ensambla los consumidores del Sprint 2 (cascada) y valida los criterios §12 del spec
de extremo a extremo, sobre el Event Store real (integración) + puertos Fake para los
sistemas externos (Odoo/Stripe), igual disciplina que el resto del sprint. La
validación con Odoo/Stripe EN VIVO es el despliegue del Sprint 2 (post-aprobación).

§12: pago → Ledger → factura.pagada → CFDI (o pendiente reintetable, pago válido) →
Policy reactiva solo si cumple → notificación → Estado de Cuenta desde el Ledger;
idempotencia; conciliación; reactivación por servicio; Motor sin Stripe directo.
"""
import ast
import inspect

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.capabilities.events import EventStore
from app.capabilities.events.catalog import CatalogedEventStore
from app.capabilities.cobranza import CobranzaCascade
from app.capabilities.payments.application import FakeAccountingPayments, PaymentApplication
from app.capabilities.cfdi import EMITTED, PENDING_RETRIABLE, CfdiConsumer, FakeCfdiPort
from app.capabilities.reactivation import FakeReactivationPort, ReactivationPolicy, ReactivationPort, ServiceState
from app.capabilities.notifications import FakeNotificationChannel, NotificationsConsumer
from app.capabilities.ledger import FakeAccountingAdapter, Ledger, Movement, CHARGE, PAYMENT
import app.capabilities.payments.service as motor_module

PID = "pi_e2e"
PARTNER = 25043


@pytest.fixture
def store():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, future=True)()
    try:
        yield CatalogedEventStore(EventStore(db))
    finally:
        db.close()


def _start_payment(store, invoice_ids, amount):
    """Equivalente a startPayment (S2-007): publica pago.iniciado."""
    store.append(event_id="ini-%s" % PID, type="pago.iniciado", aggregate_id="payment:%s" % PID,
                 payload={"payment_id": PID, "partner_id": PARTNER, "invoice_ids": invoice_ids,
                          "amount": amount, "currency": "MXN", "status": "processing"})


def _webhook_confirm(store):
    """Equivalente al webhook (S2-008): publica pago.confirmado."""
    store.append(event_id="evt-%s" % PID, type="pago.confirmado", aggregate_id="payment:%s" % PID,
                 payload={"payment_id": PID, "status": "confirmed"})


class _StatefulReactPort(ReactivationPort):
    """Puerto de reactivación realista: al reactivar, el servicio deja de estar
    suspendido (como Odoo) → otra factura del mismo servicio ya no lo reactiva."""

    def __init__(self, invoice_to_service: dict, suspended: set):
        self._map = dict(invoice_to_service)
        self._suspended = set(suspended)
        self.reactivated: list[int] = []

    def service_state(self, invoice_id):
        sid = self._map.get(invoice_id)
        return ServiceState(sid, sid in self._suspended, False) if sid is not None else None

    def reactivate(self, service_id):
        self.reactivated.append(service_id)
        self._suspended.discard(service_id)
        return True


def _cascade(store, *, paid, already_paid=None, cfdi_fail=0):
    application = PaymentApplication(FakeAccountingPayments(paid=paid, already_paid=already_paid or []), store)
    cfdi = CfdiConsumer(FakeCfdiPort(fail_times=cfdi_fail, uuid="UUID-E2E"))
    react_port = _StatefulReactPort({inv: 7 for inv in paid}, suspended={7})
    reactivation = ReactivationPolicy(react_port, store)
    notif = FakeNotificationChannel()
    notifications = NotificationsConsumer(notif, store)
    return CobranzaCascade(application, cfdi, reactivation, notifications), cfdi._cfdi, react_port, notif


def _types(store, t):
    return [e.payload for e in store.read(type=t)]


# ===== 1. Camino feliz §12 completo =====
def test_e2e_happy_path(store):
    _start_payment(store, [1, 2], 7050.0)
    _webhook_confirm(store)
    cascade, cfdi_port, react_port, notif = _cascade(store, paid=[1, 2])
    out = cascade.on_payment_confirmed(PID)

    assert out.applied is True and sorted(out.paid_invoice_ids) == [1, 2]
    # factura.pagada por cada factura
    assert sorted(p["invoice_id"] for p in _types(store, "factura.pagada")) == [1, 2]
    # CFDI emitido para ambas
    assert cfdi_port.calls == [1, 2] and all(i in cfdi_port._emitted for i in (1, 2))
    # reactivación por servicio (suspendido + sin otras vencidas)
    assert react_port.reactivated == [7]
    assert [p["service_id"] for p in _types(store, "servicio.reactivado")] == [7]
    # notificación una vez
    assert len(notif.sent) == 1 and notif.sent[0][0] == PARTNER


# ===== 2. Idempotencia: se aplica/propaga una sola vez =====
def test_e2e_idempotente(store):
    _start_payment(store, [1, 2], 7050.0)
    _webhook_confirm(store)
    cascade, cfdi_port, react_port, notif = _cascade(store, paid=[1, 2])
    cascade.on_payment_confirmed(PID)
    out2 = cascade.on_payment_confirmed(PID)   # reintento
    assert out2.applied is False
    assert len(_types(store, "factura.pagada")) == 2      # sin duplicar
    assert react_port.reactivated == [7]                 # una sola vez
    assert len(notif.sent) == 1                           # una sola notificación


# ===== 3. Conciliación: no duplica con depósito ya pagado =====
def test_e2e_conciliacion(store):
    _start_payment(store, [1, 2], 7050.0)
    _webhook_confirm(store)
    # factura 2 ya pagada por depósito OXXO/banco
    cascade, *_ = _cascade(store, paid=[1], already_paid=[2])
    cascade.on_payment_confirmed(PID)
    assert sorted(p["invoice_id"] for p in _types(store, "factura.pagada")) == [1]  # solo la 1


# ===== 4. CFDI: fallo del PAC → pendiente reintetable, pago SIGUE VÁLIDO =====
def test_e2e_cfdi_pac_falla_pago_valido(store):
    _start_payment(store, [1], 6050.0)
    _webhook_confirm(store)
    cascade, cfdi_port, *_ = _cascade(store, paid=[1], cfdi_fail=1)
    out = cascade.on_payment_confirmed(PID)   # no debe lanzar
    assert out.applied is True
    assert len(_types(store, "factura.pagada")) == 1          # el pago se aplicó (válido)
    # CFDI quedó pendiente reintetable; un reintento posterior timbra
    assert CfdiConsumer(cfdi_port).on_factura_pagada(1).status == EMITTED


# ===== 5. Reactivación por servicio (multi) y condiciones =====
def test_e2e_reactivacion_por_servicio(store):
    _start_payment(store, [1, 2], 7050.0)
    _webhook_confirm(store)
    application = PaymentApplication(FakeAccountingPayments(paid=[1, 2]), store)
    cfdi = CfdiConsumer(FakeCfdiPort())
    # factura 1 -> servicio 7 (suspendido, reactivable); factura 2 -> servicio 8 (con otras vencidas)
    states = {1: ServiceState(7, True, False), 2: ServiceState(8, True, True)}
    react_port = FakeReactivationPort(states)
    reactivation = ReactivationPolicy(react_port, store)
    notifications = NotificationsConsumer(FakeNotificationChannel(), store)
    CobranzaCascade(application, cfdi, reactivation, notifications).on_payment_confirmed(PID)
    assert react_port.reactivated == [7]                 # solo el que cumple las 3 condiciones
    assert [p["service_id"] for p in _types(store, "servicio.reactivado")] == [7]


# ===== 6. Estado de Cuenta desde el Ledger =====
def test_e2e_estado_de_cuenta_desde_ledger():
    # Antes del pago: factura abierta vencida.
    antes = Ledger(FakeAccountingAdapter([
        Movement(1, CHARGE, "2026-06-01", 6050.0, "MXN", "INV-1", "not_paid", None, "2026-06-11", 6050.0),
    ])).account_statement(today=__import__("datetime").date(2026, 6, 30))
    assert antes.balance == 6050.0 and antes.overdue == 6050.0
    # Después del pago: residual 0 + un pago registrado.
    despues = Ledger(FakeAccountingAdapter([
        Movement(1, CHARGE, "2026-06-01", 6050.0, "MXN", "INV-1", "paid", None, "2026-06-11", 0.0),
        Movement(9, PAYMENT, "2026-06-30", 6050.0, "MXN", "PAY-1"),
    ])).account_statement(today=__import__("datetime").date(2026, 6, 30))
    assert despues.balance == 0.0 and despues.overdue == 0.0


# ===== 7. Motor de Pago sin referencia directa a Stripe =====
def test_e2e_motor_sin_stripe():
    tree = ast.parse(inspect.getsource(motor_module))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "stripe" not in imported

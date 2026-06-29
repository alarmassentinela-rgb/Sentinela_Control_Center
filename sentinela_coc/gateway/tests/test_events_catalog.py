# -*- coding: utf-8 -*-
"""Pruebas del Catálogo de eventos de Cobranza (S2-002).

Verifican: cada tipo tiene criticidad + esquema mínimo; los 3 alias vienen de
Suscripciones; `append` (vía CatalogedEventStore) RECHAZA un tipo desconocido y
exige el esquema mínimo; lectura delegada al store agnóstico.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.capabilities.events import EventRecord, EventStore
from app.capabilities.events.catalog import (
    CATALOG,
    CatalogedEventStore,
    Criticality,
    InvalidEventPayload,
    UnknownEventType,
    criticality,
    is_known,
    validate,
)

COBRANZA = ["pago.iniciado", "pago.confirmado", "pago.rechazado", "factura.pagada", "servicio.reactivado"]
ALIAS_SUSCRIPCIONES = ["factura.creada", "factura.por_vencer", "servicio.suspendido"]


@pytest.fixture
def cstore():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = Session()
    try:
        yield CatalogedEventStore(EventStore(db)), db
    finally:
        db.close()


def test_catalogo_completo_con_criticidad_y_esquema_minimo():
    # los 5 de Cobranza + 3 alias, y nada más
    assert set(CATALOG) == set(COBRANZA) | set(ALIAS_SUSCRIPCIONES)
    for name, et in CATALOG.items():
        assert isinstance(et.criticality, Criticality)        # criticidad
        assert len(et.required_keys) >= 1                     # esquema mínimo (no vacío)


def test_alias_de_suscripciones_marcados():
    for n in ALIAS_SUSCRIPCIONES:
        assert CATALOG[n].origin == "suscripciones"
    for n in COBRANZA:
        assert CATALOG[n].origin == "cobranza"


def test_helpers_is_known_y_criticality():
    assert is_known("pago.confirmado") is True
    assert is_known("foo.bar") is False
    assert criticality("pago.confirmado") == Criticality.CRITICAL
    assert criticality("pago.iniciado") == Criticality.INFO


def test_validate_rechaza_tipo_desconocido():
    with pytest.raises(UnknownEventType):
        validate("foo.bar", {"x": 1})


def test_validate_exige_esquema_minimo():
    with pytest.raises(InvalidEventPayload):
        validate("pago.confirmado", {})           # falta payment_id
    validate("pago.confirmado", {"payment_id": "p1"})   # OK, no levanta


def test_append_rechaza_tipo_desconocido_y_no_almacena(cstore):
    store, db = cstore
    with pytest.raises(UnknownEventType):
        store.append("e1", "evento.inexistente", "agg:1", {"x": 1})
    assert db.query(EventRecord).count() == 0     # nada se almacenó


def test_append_tipo_conocido_ok(cstore):
    store, db = cstore
    r = store.append("e1", "pago.confirmado", "payment:1", {"payment_id": "p1"})
    assert r.created is True
    assert db.query(EventRecord).count() == 1
    assert store.by_aggregate("payment:1")[0].event_id == "e1"


def test_append_rechaza_esquema_minimo_incompleto(cstore):
    store, db = cstore
    with pytest.raises(InvalidEventPayload):
        store.append("e1", "factura.pagada", "invoice:1", {})   # falta invoice_id
    assert db.query(EventRecord).count() == 0


def test_lectura_delegada_al_store_agnostico(cstore):
    store, _ = cstore
    store.append("e1", "pago.iniciado", "payment:1", {"payment_id": "p1"})
    store.append("e2", "pago.confirmado", "payment:1", {"payment_id": "p1"})
    assert [e.event_id for e in store.read(type="pago.confirmado")] == ["e2"]
    assert [e.event_id for e in store.by_aggregate("payment:1")] == ["e1", "e2"]

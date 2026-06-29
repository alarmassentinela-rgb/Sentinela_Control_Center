# -*- coding: utf-8 -*-
"""Pruebas del Event Store mínimo (S2-001).

Verifican el contrato aprobado: append / read / by_aggregate + idempotencia por
event_id, orden de almacenamiento, y que la superficie pública es MÍNIMA (sin
replay/projections/cqrs).
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.capabilities.events import EventRecord, EventStore  # importar registra el modelo en Base


@pytest.fixture
def store():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = Session()
    try:
        yield EventStore(db)
    finally:
        db.close()


def test_append_and_read(store):
    r = store.append("evt-1", "pago.confirmado", "payment:1", {"monto": 6050})
    assert r.created is True
    assert r.event.event_id == "evt-1"
    assert r.event.type == "pago.confirmado"
    assert r.event.aggregate_id == "payment:1"
    assert r.event.payload == {"monto": 6050}
    assert r.event.seq >= 1
    assert r.event.created_at is not None

    todos = store.read()
    assert len(todos) == 1
    assert todos[0].event_id == "evt-1"


def test_append_idempotente_por_event_id(store):
    store.append("evt-dup", "pago.confirmado", "payment:1", {"v": 1})
    # mismo event_id, payload distinto -> NO inserta de nuevo; conserva el original
    r2 = store.append("evt-dup", "pago.confirmado", "payment:1", {"v": 999})
    assert r2.created is False
    assert r2.event.payload == {"v": 1}          # se conserva el primero
    assert len(store.read()) == 1                # una sola fila
    assert store.db.query(EventRecord).count() == 1


def test_read_filtra_por_tipo(store):
    store.append("a", "pago.confirmado", "payment:1", {})
    store.append("b", "pago.rechazado", "payment:2", {})
    store.append("c", "pago.confirmado", "payment:3", {})
    confirmados = store.read(type="pago.confirmado")
    assert [e.event_id for e in confirmados] == ["a", "c"]
    assert [e.event_id for e in store.read(type="pago.rechazado")] == ["b"]


def test_by_aggregate_solo_del_agregado_y_en_orden(store):
    store.append("a1", "pago.iniciado", "payment:1", {})
    store.append("b1", "pago.iniciado", "payment:2", {})
    store.append("a2", "pago.confirmado", "payment:1", {})
    eventos = store.by_aggregate("payment:1")
    assert [e.event_id for e in eventos] == ["a1", "a2"]   # orden de almacenamiento
    assert all(e.aggregate_id == "payment:1" for e in eventos)
    assert store.by_aggregate("payment:404") == []


def test_orden_de_almacenamiento_y_after_seq(store):
    r1 = store.append("e1", "x", "agg", {})
    store.append("e2", "x", "agg", {})
    store.append("e3", "x", "agg", {})
    seqs = [e.seq for e in store.read()]
    assert seqs == sorted(seqs)                   # estrictamente en orden de append
    # lectura incremental: solo lo posterior a un seq dado
    posteriores = store.read(after_seq=r1.event.seq)
    assert [e.event_id for e in posteriores] == ["e2", "e3"]


def test_limit(store):
    for i in range(5):
        store.append(f"e{i}", "x", "agg", {})
    assert len(store.read(limit=2)) == 2


def test_superficie_publica_minima():
    """El Event Store expone SOLO append/read/by_aggregate (sin replay/projections/cqrs)."""
    publicos = {m for m in dir(EventStore) if not m.startswith("_")}
    assert publicos == {"append", "read", "by_aggregate"}

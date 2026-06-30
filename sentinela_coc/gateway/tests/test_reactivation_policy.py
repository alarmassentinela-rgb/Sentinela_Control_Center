# -*- coding: utf-8 -*-
"""Pruebas de la Reactivation Policy (S2-011).

Reactiva SOLO si se cumplen las 3 condiciones; por servicio (multi-servicio reactiva
solo el liquidado); no reactiva si quedan vencidas; publica servicio.reactivado;
idempotente.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.capabilities.events import EventStore
from app.capabilities.events.catalog import CatalogedEventStore
from app.capabilities.reactivation import (
    FakeReactivationPort,
    ReactivationPolicy,
    ReactivationPort,
    ServiceState,
)


@pytest.fixture
def store():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, future=True)()
    try:
        yield CatalogedEventStore(EventStore(db))
    finally:
        db.close()


def _reactivados(store):
    return sorted(e.payload["service_id"] for e in store.read(type="servicio.reactivado"))


def test_reactiva_si_cumple_las_tres_condiciones(store):
    port = FakeReactivationPort({101: ServiceState(7, suspended_for_collections=True, has_other_overdue=False)})
    out = ReactivationPolicy(port, store).on_factura_pagada(101)
    assert out.reactivated is True and out.service_id == 7
    assert port.reactivated == [7]
    assert _reactivados(store) == [7]


def test_no_reactiva_si_no_esta_suspendido(store):
    port = FakeReactivationPort({101: ServiceState(7, suspended_for_collections=False, has_other_overdue=False)})
    out = ReactivationPolicy(port, store).on_factura_pagada(101)
    assert out.reactivated is False and out.reason == "no_suspendido"
    assert port.reactivated == [] and _reactivados(store) == []


def test_no_reactiva_si_hay_otras_vencidas(store):
    port = FakeReactivationPort({101: ServiceState(7, suspended_for_collections=True, has_other_overdue=True)})
    out = ReactivationPolicy(port, store).on_factura_pagada(101)
    assert out.reactivated is False and out.reason == "otras_vencidas"
    assert port.reactivated == [] and _reactivados(store) == []


def test_por_servicio_multi_reactiva_solo_el_liquidado(store):
    # factura 101 -> servicio 7 (reactivable); factura 202 -> servicio 8 (no liquidado/no suspendido)
    port = FakeReactivationPort({
        101: ServiceState(7, suspended_for_collections=True, has_other_overdue=False),
        202: ServiceState(8, suspended_for_collections=False, has_other_overdue=False),
    })
    policy = ReactivationPolicy(port, store)
    policy.on_factura_pagada(101)
    policy.on_factura_pagada(202)
    assert port.reactivated == [7]          # solo el liquidado
    assert _reactivados(store) == [7]


def test_idempotente(store):
    port = FakeReactivationPort({101: ServiceState(7, suspended_for_collections=True, has_other_overdue=False)})
    policy = ReactivationPolicy(port, store)
    policy.on_factura_pagada(101)
    out2 = policy.on_factura_pagada(101)    # reintento
    assert out2.reactivated is False and out2.reason == "ya_reactivado"
    assert port.reactivated == [7]          # una sola vez
    assert _reactivados(store) == [7]


def test_sin_servicio_no_reactiva(store):
    port = FakeReactivationPort({101: None})
    out = ReactivationPolicy(port, store).on_factura_pagada(101)
    assert out.reactivated is False and out.reason == "sin_servicio"


def test_fake_es_reactivation_port():
    assert isinstance(FakeReactivationPort({}), ReactivationPort)

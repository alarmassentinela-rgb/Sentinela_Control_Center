# -*- coding: utf-8 -*-
"""Pruebas del CFDI asíncrono reintetable (S2-010).

factura.pagada → timbrado; PAC falla → pending_retriable (pago sigue válido, sin
excepción); reintento exitoso; idempotencia (no re-timbra).
"""
from app.capabilities.cfdi import (
    EMITTED,
    PENDING_RETRIABLE,
    CfdiConsumer,
    CfdiPort,
    FakeCfdiPort,
)


def test_timbra_al_pagar():
    port = FakeCfdiPort(uuid="UUID-7")
    res = CfdiConsumer(port).on_factura_pagada(101)
    assert res.status == EMITTED and res.uuid == "UUID-7"
    assert port.calls == [101]


def test_pac_falla_queda_pendiente_reintetable_sin_excepcion():
    port = FakeCfdiPort(fail_times=1)
    res = CfdiConsumer(port).on_factura_pagada(101)   # no debe lanzar
    assert res.status == PENDING_RETRIABLE and res.reason == "pac_timeout"


def test_reintento_exitoso():
    port = FakeCfdiPort(fail_times=1, uuid="UUID-9")
    c = CfdiConsumer(port)
    r1 = c.on_factura_pagada(101)
    r2 = c.on_factura_pagada(101)                      # reintento
    assert r1.status == PENDING_RETRIABLE
    assert r2.status == EMITTED and r2.uuid == "UUID-9"


def test_idempotente_no_retimbra():
    port = FakeCfdiPort(uuid="UUID-1")
    c = CfdiConsumer(port)
    r1 = c.on_factura_pagada(101)
    r2 = c.on_factura_pagada(101)
    assert r1.status == EMITTED and r2.status == EMITTED
    assert r1.uuid == r2.uuid == "UUID-1"              # mismo UUID, no re-timbra


def test_error_inesperado_no_invalida_el_pago():
    # Cualquier excepción del puerto se traduce a pending_retriable (el pago sigue válido).
    port = FakeCfdiPort(raise_exc=RuntimeError("boom"))
    res = CfdiConsumer(port).on_factura_pagada(101)
    assert res.status == PENDING_RETRIABLE and "boom" in (res.reason or "")


def test_fake_es_cfdi_port():
    assert isinstance(FakeCfdiPort(), CfdiPort)

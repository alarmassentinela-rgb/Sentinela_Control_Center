# -*- coding: utf-8 -*-
"""CFDI asíncrono reintetable (S2-010) — consumidor de `factura.pagada`.

Al pagarse una factura, dispara el timbrado CFDI vía un PUERTO (reusa el timbrado
existente de `sentinela_cfdi_prodigia` en Odoo). DESACOPLADO del pago: si el PAC
falla, el resultado es `pending_retriable` (NUNCA lanza hacia el flujo de pago), el
PAGO SIGUE VÁLIDO y el CFDI puede reintentarse. Idempotente: una factura ya timbrada
devuelve `emitted` sin volver a timbrar.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

EMITTED = "emitted"
PENDING_RETRIABLE = "pending_retriable"


@dataclass(frozen=True)
class CfdiResult:
    status: str                 # EMITTED | PENDING_RETRIABLE
    uuid: str | None = None
    reason: str | None = None


class CfdiPort(ABC):
    """Puerto hacia el timbrado CFDI (Odoo/Prodigia). Idempotente y reintetable."""

    @abstractmethod
    def stamp(self, invoice_id: int) -> CfdiResult:
        ...


class CfdiConsumer:
    """Consumidor de `factura.pagada`. Garantiza que un fallo del CFDI NUNCA rompe el
    flujo de pago: cualquier error se traduce a `pending_retriable`."""

    def __init__(self, cfdi_port: CfdiPort):
        self._cfdi = cfdi_port

    def on_factura_pagada(self, invoice_id: int) -> CfdiResult:
        try:
            return self._cfdi.stamp(invoice_id)
        except Exception as e:   # noqa: BLE001 — el CFDI jamás invalida el pago
            return CfdiResult(PENDING_RETRIABLE, reason=str(e) or "cfdi_error")


class FakeCfdiPort(CfdiPort):
    """Para pruebas: falla N veces (simula PAC caído), luego timbra. Idempotente."""

    def __init__(self, fail_times: int = 0, uuid: str = "UUID-FAKE", raise_exc: Exception | None = None):
        self._fail_times = fail_times
        self._uuid = uuid
        self._raise = raise_exc
        self._emitted: dict[int, str] = {}
        self.calls: list[int] = []

    def stamp(self, invoice_id: int) -> CfdiResult:
        self.calls.append(invoice_id)
        if invoice_id in self._emitted:                      # idempotencia
            return CfdiResult(EMITTED, uuid=self._emitted[invoice_id])
        if self._raise is not None:
            raise self._raise
        if self._fail_times > 0:                             # PAC caído → reintetable (sin excepción)
            self._fail_times -= 1
            return CfdiResult(PENDING_RETRIABLE, reason="pac_timeout")
        self._emitted[invoice_id] = self._uuid
        return CfdiResult(EMITTED, uuid=self._uuid)


class OdooCfdiPort(CfdiPort):
    """Implementación real: endpoint interno de Odoo que timbra vía Prodigia."""

    def __init__(self, base_url: str, shared_secret: str):
        self._base = base_url.rstrip("/")
        self._secret = shared_secret

    def stamp(self, invoice_id: int) -> CfdiResult:
        import httpx
        payload = {"jsonrpc": "2.0", "method": "call", "params": {"invoice_id": invoice_id}}
        r = httpx.post("%s/coc/internal/cfdi/stamp" % self._base, json=payload,
                       headers={"X-COC-Secret": self._secret}, timeout=40)
        r.raise_for_status()
        res = (r.json() or {}).get("result") or {}
        if not res.get("ok"):
            return CfdiResult(PENDING_RETRIABLE, reason=res.get("error") or "cfdi_error")
        return CfdiResult(res.get("status") or PENDING_RETRIABLE,
                          uuid=res.get("uuid"), reason=res.get("reason"))

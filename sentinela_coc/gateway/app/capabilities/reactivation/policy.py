# -*- coding: utf-8 -*-
"""Reactivation Policy (S2-011) — consumidor de `factura.pagada`.

Evalúa ÚNICAMENTE la política de reactivación. Reactiva el servicio (POR SERVICIO)
solo si se cumplen las TRES condiciones aprobadas y publica `servicio.reactivado`.

Condiciones (todas):
  1. Factura totalmente pagada  → garantizada por el disparador `factura.pagada`.
  2. Servicio suspendido por cobranza.
  3. No existen otras facturas vencidas del servicio.

NO mezcla lógica de pagos, CFDI ni notificaciones. Odoo queda encapsulado tras el
puerto (`ReactivationPort`): el puerto entrega HECHOS y ejecuta la acción; la POLÍTICA
(decisión) vive aquí.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceState:
    """Hechos del servicio asociado a una factura (los provee el puerto)."""
    service_id: int
    suspended_for_collections: bool   # condición 2
    has_other_overdue: bool           # negación de la condición 3


@dataclass(frozen=True)
class ReactivationOutcome:
    reactivated: bool
    service_id: int | None = None
    reason: str | None = None


class ReactivationPort(ABC):
    @abstractmethod
    def service_state(self, invoice_id: int) -> ServiceState | None:
        """Servicio de la factura + hechos para la política (None si no hay servicio)."""

    @abstractmethod
    def reactivate(self, service_id: int) -> bool:
        """Reactiva el servicio en el sistema dueño (idempotente)."""


class ReactivationPolicy:
    def __init__(self, port: ReactivationPort, store):
        self._port = port
        self._store = store   # CatalogedEventStore

    def on_factura_pagada(self, invoice_id: int) -> ReactivationOutcome:
        state = self._port.service_state(invoice_id)
        if state is None:
            return ReactivationOutcome(False, reason="sin_servicio")
        # Condición 1 (factura pagada) la garantiza el disparador factura.pagada.
        if not state.suspended_for_collections:               # condición 2
            return ReactivationOutcome(False, state.service_id, "no_suspendido")
        if state.has_other_overdue:                           # condición 3
            return ReactivationOutcome(False, state.service_id, "otras_vencidas")

        # Idempotencia: ¿ya reactivado por esta factura?
        ev_id = "reactivado:%s:%s" % (state.service_id, invoice_id)
        if any(e.event_id == ev_id for e in self._store.read(type="servicio.reactivado")):
            return ReactivationOutcome(False, state.service_id, "ya_reactivado")

        self._port.reactivate(state.service_id)
        self._store.append(
            event_id=ev_id,
            type="servicio.reactivado",
            aggregate_id="service:%s" % state.service_id,
            payload={"service_id": state.service_id, "invoice_id": invoice_id},
        )
        return ReactivationOutcome(True, state.service_id)


class FakeReactivationPort(ReactivationPort):
    """Para pruebas: estados predefinidos por factura; registra reactivaciones."""

    def __init__(self, states: dict[int, ServiceState | None]):
        self._states = states
        self.reactivated: list[int] = []

    def service_state(self, invoice_id: int) -> ServiceState | None:
        return self._states.get(invoice_id)

    def reactivate(self, service_id: int) -> bool:
        self.reactivated.append(service_id)
        return True


class OdooReactivationPort(ReactivationPort):
    """Implementación real: endpoints internos de Odoo (sentinela_subscriptions:
    state=='suspension' + action_reactivate). Validación viva: S2-015."""

    def __init__(self, base_url: str, shared_secret: str):
        self._base = base_url.rstrip("/")
        self._secret = shared_secret

    def _call(self, path: str, params: dict) -> dict:
        import httpx
        payload = {"jsonrpc": "2.0", "method": "call", "params": params}
        r = httpx.post("%s%s" % (self._base, path), json=payload,
                       headers={"X-COC-Secret": self._secret}, timeout=20)
        r.raise_for_status()
        return (r.json() or {}).get("result") or {}

    def service_state(self, invoice_id: int) -> ServiceState | None:
        res = self._call("/coc/internal/reactivation/service_state", {"invoice_id": invoice_id})
        if not res.get("ok") or not res.get("service_id"):
            return None
        return ServiceState(
            service_id=res["service_id"],
            suspended_for_collections=bool(res.get("suspended_for_collections")),
            has_other_overdue=bool(res.get("has_other_overdue")),
        )

    def reactivate(self, service_id: int) -> bool:
        res = self._call("/coc/internal/reactivation/reactivate", {"service_id": service_id})
        return bool(res.get("ok"))

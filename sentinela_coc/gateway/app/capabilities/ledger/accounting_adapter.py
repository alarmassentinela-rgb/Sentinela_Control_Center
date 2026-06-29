# -*- coding: utf-8 -*-
"""Adaptador contable de lectura (S2-003) — puerto del Ledger hacia el sistema
contable activo (hoy Odoo).

El **Ledger** (S2-004) dependerá EXCLUSIVAMENTE de `AccountingAdapter`, nunca de
Odoo. Así la verdad financiera vive en el contable existente (no se duplica) y el
contable es reemplazable cambiando el adaptador.

Este adaptador es de SOLO LECTURA: devuelve movimientos NORMALIZADOS
(cargos/pagos/notas) del cliente. El signo y el cálculo del Estado de Cuenta son
responsabilidad del Ledger (S2-004), no del adaptador.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

CHARGE = "charge"     # cargo (factura)
PAYMENT = "payment"   # pago
NOTE = "note"         # nota (crédito/ajuste/bonificación)
KINDS = (CHARGE, PAYMENT, NOTE)


@dataclass(frozen=True)
class Movement:
    """Movimiento contable normalizado (agnóstico del contable de origen)."""
    id: int
    kind: str            # CHARGE | PAYMENT | NOTE
    date: str            # fecha ISO (str) — portable
    amount: float        # MAGNITUD positiva; el signo lo aplica el Ledger por `kind`
    currency: str
    reference: str
    status: str | None = None
    service_id: int | None = None


class AccountingUnavailable(RuntimeError):
    """El sistema contable no respondió correctamente."""
    def __init__(self, status):
        super().__init__("accounting_unavailable: %s" % status)
        self.status = status


def _to_movement(d: dict) -> Movement:
    kind = d.get("kind")
    if kind not in KINDS:
        raise ValueError("kind desconocido: %r" % kind)
    return Movement(
        id=int(d["id"]),
        kind=kind,
        date=str(d.get("date") or ""),
        amount=round(float(d.get("amount") or 0.0), 2),
        currency=d.get("currency") or "MXN",
        reference=d.get("reference") or "",
        status=d.get("status"),
        service_id=d.get("service_id"),
    )


class AccountingAdapter(ABC):
    """Puerto: lee movimientos normalizados del cliente (opcionalmente por servicio)."""

    @abstractmethod
    def movements(self, service_id: int | None = None) -> list[Movement]:
        ...


class OdooAccountingAdapter(AccountingAdapter):
    """Implementación sobre Odoo, vía la sesión efímera del cliente (act-as): las
    record rules acotan los datos a ese cliente. Encapsula a Odoo por completo."""

    def __init__(self, odoo_client, odoo_session_id: str):
        self._odoo = odoo_client
        self._sid = odoo_session_id

    def movements(self, service_id: int | None = None) -> list[Movement]:
        params = {} if service_id is None else {"service_id": service_id}
        status, body = self._odoo.get_json_as(self._sid, "/v1/ledger/movements", params)
        if status != 200 or not isinstance(body, dict):
            raise AccountingUnavailable(status)
        return [_to_movement(it) for it in body.get("items", [])]


class FakeAccountingAdapter(AccountingAdapter):
    """Para pruebas (sin Odoo): devuelve movimientos predefinidos, filtra por servicio."""

    def __init__(self, items: list[Movement]):
        self._items = list(items)

    def movements(self, service_id: int | None = None) -> list[Movement]:
        if service_id is None:
            return list(self._items)
        return [m for m in self._items if m.service_id == service_id]

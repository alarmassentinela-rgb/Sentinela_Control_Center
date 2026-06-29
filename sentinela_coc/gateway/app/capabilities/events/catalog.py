# -*- coding: utf-8 -*-
"""Catálogo de eventos de Cobranza (S2-002).

Capa de DOMINIO (Cobranza) sobre el Event Store agnóstico de S2-001. Define los
tipos de evento que Cobranza produce/consume, su **criticidad** y su **esquema
mínimo** (claves obligatorias del payload).

Invariante #1 (aprobado): el Event Store permanece agnóstico del dominio. Por eso
este catálogo NO modifica el store: lo **envuelve** (`CatalogedEventStore`) y valida
antes de delegar. `append` rechaza un tipo desconocido (y exige el esquema mínimo).
"""
from dataclasses import dataclass
from enum import Enum

from .store import AppendResult, EventStore


class Criticality(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class UnknownEventType(ValueError):
    """El tipo de evento no está en el catálogo de Cobranza."""


class InvalidEventPayload(ValueError):
    """Falta alguna clave del esquema mínimo del evento."""


@dataclass(frozen=True)
class EventType:
    name: str
    criticality: Criticality
    required_keys: tuple[str, ...]   # esquema mínimo (claves obligatorias del payload)
    origin: str                      # "cobranza" | "suscripciones" (alias reusado)


def _t(name, crit, required, origin="cobranza") -> EventType:
    return EventType(name, crit, tuple(required), origin)


# Catálogo MÍNIMO (spec §7). Los 5 eventos propios de Cobranza + 3 alias que ya
# produce Suscripciones (se reusan, no se reinventan).
CATALOG: dict[str, EventType] = {t.name: t for t in (
    _t("pago.iniciado",       Criticality.INFO,     ["payment_id"]),
    _t("pago.confirmado",     Criticality.CRITICAL, ["payment_id"]),
    _t("pago.rechazado",      Criticality.WARNING,  ["payment_id"]),
    _t("factura.pagada",      Criticality.CRITICAL, ["invoice_id"]),
    _t("servicio.reactivado", Criticality.WARNING,  ["service_id"]),
    # Alias reusados de Suscripciones
    _t("factura.creada",      Criticality.INFO,     ["invoice_id"], origin="suscripciones"),
    _t("factura.por_vencer",  Criticality.WARNING,  ["invoice_id"], origin="suscripciones"),
    _t("servicio.suspendido", Criticality.CRITICAL, ["service_id"], origin="suscripciones"),
)}


def is_known(name: str) -> bool:
    return name in CATALOG


def get(name: str) -> EventType:
    try:
        return CATALOG[name]
    except KeyError:
        raise UnknownEventType(name)


def criticality(name: str) -> Criticality:
    return get(name).criticality


def validate(name: str, payload: dict | None = None) -> None:
    """Rechaza tipo desconocido (UnknownEventType) y exige el esquema mínimo
    (InvalidEventPayload si falta alguna clave obligatoria)."""
    et = get(name)
    missing = [k for k in et.required_keys if k not in (payload or {})]
    if missing:
        raise InvalidEventPayload("%s: faltan claves mínimas %s" % (name, missing))


class CatalogedEventStore:
    """Event Store con el catálogo de Cobranza. `append` valida contra el catálogo
    antes de delegar en el Event Store agnóstico; `read`/`by_aggregate` se delegan
    sin restricción (la lectura no está gobernada por el catálogo)."""

    def __init__(self, store: EventStore):
        self._store = store

    def append(self, event_id: str, type: str, aggregate_id: str,
               payload: dict | None = None) -> AppendResult:
        validate(type, payload)
        return self._store.append(event_id, type, aggregate_id, payload)

    def read(self, **kw):
        return self._store.read(**kw)

    def by_aggregate(self, aggregate_id: str):
        return self._store.by_aggregate(aggregate_id)

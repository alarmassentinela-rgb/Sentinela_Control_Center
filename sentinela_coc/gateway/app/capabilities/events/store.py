# -*- coding: utf-8 -*-
"""Event Store mínimo (S2-001) — capacidad de la plataforma, nacida para Cobranza.

Expone EXACTAMENTE tres operaciones (contrato congelado del Sprint 2):
  - append(...)        publica un evento (IDEMPOTENTE por event_id)
  - read(...)          recupera eventos por filtro, en orden de almacenamiento
  - by_aggregate(...)  recupera los eventos de un agregado

NO incluye (y no debe incluir en este sprint): CQRS, Event Sourcing, Replay,
Projections, Timeline, suscripciones avanzadas ni infraestructura futura.
"""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import EventRecord


@dataclass(frozen=True)
class Event:
    """Evento almacenado (valor inmutable; desacopla a los consumidores del ORM)."""
    event_id: str
    type: str
    aggregate_id: str
    payload: dict
    seq: int            # orden de almacenamiento
    created_at: datetime


@dataclass(frozen=True)
class AppendResult:
    event: Event
    created: bool       # False = el event_id ya existía (idempotencia / dedupe)


def _to_event(rec: EventRecord) -> Event:
    return Event(
        event_id=rec.event_id, type=rec.type, aggregate_id=rec.aggregate_id,
        payload=rec.payload or {}, seq=rec.seq, created_at=rec.created_at,
    )


class EventStore:
    """Almacén de eventos sobre la BD propia del gateway. El llamador controla el
    commit de la sesión (igual que el resto de servicios del gateway)."""

    def __init__(self, db: Session):
        self.db = db

    def append(self, event_id: str, type: str, aggregate_id: str,
               payload: dict | None = None) -> AppendResult:
        """Publica un evento. IDEMPOTENTE: si el event_id ya existe, NO inserta de
        nuevo y devuelve el existente con created=False (el payload original se
        conserva). La unicidad de event_id es además garantía a nivel de BD."""
        existing = self.db.query(EventRecord).filter(EventRecord.event_id == event_id).one_or_none()
        if existing is not None:
            return AppendResult(_to_event(existing), created=False)

        rec = EventRecord(event_id=event_id, type=type, aggregate_id=aggregate_id,
                          payload=payload or {})
        try:
            # Savepoint: ante una carrera con el mismo event_id, solo se revierte
            # este insert (no el resto de la transacción del llamador).
            with self.db.begin_nested():
                self.db.add(rec)
                self.db.flush()
            return AppendResult(_to_event(rec), created=True)
        except IntegrityError:
            dup = self.db.query(EventRecord).filter(EventRecord.event_id == event_id).one()
            return AppendResult(_to_event(dup), created=False)

    def read(self, *, type: str | None = None, aggregate_id: str | None = None,
             after_seq: int | None = None, limit: int | None = None) -> list[Event]:
        """Recupera eventos por filtro, en ORDEN de almacenamiento (seq ascendente).
        Filtros opcionales: type, aggregate_id, after_seq (para leer incrementalmente)
        y limit. Sin filtros = todos."""
        q = self.db.query(EventRecord)
        if type is not None:
            q = q.filter(EventRecord.type == type)
        if aggregate_id is not None:
            q = q.filter(EventRecord.aggregate_id == aggregate_id)
        if after_seq is not None:
            q = q.filter(EventRecord.seq > after_seq)
        q = q.order_by(EventRecord.seq.asc())
        if limit is not None:
            q = q.limit(limit)
        return [_to_event(r) for r in q.all()]

    def by_aggregate(self, aggregate_id: str) -> list[Event]:
        """Todos los eventos de un agregado, en orden de almacenamiento."""
        return self.read(aggregate_id=aggregate_id)

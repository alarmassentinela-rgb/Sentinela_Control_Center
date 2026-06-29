# -*- coding: utf-8 -*-
"""Almacén mínimo del Event Store (S2-001).

Una sola tabla. `event_id` ÚNICO = idempotencia (dedupe). `id` autoincremental =
orden de almacenamiento (secuencia) para lecturas ordenadas. Sin proyecciones,
sin event sourcing, sin replay: solo el registro de eventos que Cobranza necesita.

Fechas en UTC naïve (portabilidad SQLite[tests] ↔ Postgres[prod]), igual que el
resto del gateway.
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ...clock import utcnow
from ...db import Base


class EventRecord(Base):
    __tablename__ = "coc_event"

    # Secuencia de almacenamiento (orden total de append). NO es el id de negocio.
    seq: Mapped[int] = mapped_column("id", Integer, primary_key=True, autoincrement=True)
    # Idempotencia: lo provee el productor; ÚNICO -> un mismo evento no se inserta dos veces.
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Tipo del evento (texto libre en S2-001; el catálogo/criticidad llega en S2-002).
    type: Mapped[str] = mapped_column(String(64), index=True)
    # Agregado al que pertenece el evento (p. ej. "payment:123"); base de byAggregate.
    aggregate_id: Mapped[str] = mapped_column(String(64), index=True)
    # Datos del evento.
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

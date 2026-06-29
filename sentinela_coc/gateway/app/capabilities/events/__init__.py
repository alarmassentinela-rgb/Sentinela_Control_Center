# -*- coding: utf-8 -*-
"""Capacidad Eventos — Event Store mínimo (S2-001).

Contrato público: EventStore.append / read / by_aggregate. Nada más.
"""
from .models import EventRecord
from .store import AppendResult, Event, EventStore

__all__ = ["EventStore", "Event", "AppendResult", "EventRecord"]

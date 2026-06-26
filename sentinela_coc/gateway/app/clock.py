# -*- coding: utf-8 -*-
"""Reloj UTC naïve (portabilidad SQLite↔Postgres; reemplaza datetime.utcnow deprecado)."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

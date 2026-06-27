# -*- coding: utf-8 -*-
"""Caché TTL en memoria (BFF). Dashboard (TTL corto ~30s) + PDF/XML (TTL medio).

Proceso único (uvicorn 1 worker) → memoria local basta. Para multi-worker/escala
horizontal, sustituir por Redis manteniendo esta interfaz. Las claves SIEMPRE
incluyen el partner_id para que jamás se sirva contenido cacheado de otro cliente.
"""
import threading
from datetime import timedelta

from ..clock import utcnow


class TTLCache:
    def __init__(self):
        self._store: dict = {}
        self._lock = threading.Lock()

    def get(self, key):
        """Devuelve (value, created_at) si hay hit vigente; None si miss/expirado."""
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            value, expires_at, created_at = item
            if utcnow() >= expires_at:
                self._store.pop(key, None)
                return None
            return value, created_at

    def set(self, key, value, ttl_sec: int):
        with self._lock:
            now = utcnow()
            self._store[key] = (value, now + timedelta(seconds=ttl_sec), now)

    def invalidate(self, key):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()


cache = TTLCache()

DASHBOARD_TTL_SEC = 30
DOCUMENT_TTL_SEC = 300

"""Caché REEMPLAZABLE (principio #6): el Motor usa la interfaz CacheBackend, no una
implementación concreta. Hoy PostgreSQL; mañana Redis; después memoria distribuida —
sin tocar el Motor. Se elige por `ir.config_parameter` `catalog.cache_backend`.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import timedelta

_logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Contrato de caché. Implementaciones: Postgres (default), Redis (futuro)…"""

    @abstractmethod
    def get(self, key: str):
        """Devuelve el valor (deserializado) o None si no existe/expiró."""

    @abstractmethod
    def set(self, key: str, value, ttl_seconds: int = None):
        """Guarda value (serializable a JSON) con TTL opcional."""

    @abstractmethod
    def delete(self, key: str):
        ...

    @abstractmethod
    def stats(self) -> dict:
        """{hits, misses, ratio}."""


class PostgresCacheBackend(CacheBackend):
    """Backend por defecto: usa el modelo catalog.cache.entry."""

    def __init__(self, env):
        self.env = env
        self._hits = 0
        self._misses = 0

    def _model(self):
        return self.env["catalog.cache.entry"].sudo()

    def get(self, key):
        rec = self._model().search([("key", "=", key)], limit=1)
        if rec and rec.is_fresh():
            self._hits += 1
            return json.loads(rec.value) if rec.value else None
        self._misses += 1
        return None

    def set(self, key, value, ttl_seconds=None):
        from odoo import fields as _f
        expires = (_f.Datetime.now() + timedelta(seconds=ttl_seconds)) if ttl_seconds else False
        payload = json.dumps(value, ensure_ascii=False, default=str)
        rec = self._model().search([("key", "=", key)], limit=1)
        if rec:
            rec.write({"value": payload, "expires_at": expires})
        else:
            self._model().create({"key": key, "value": payload, "expires_at": expires})

    def delete(self, key):
        self._model().search([("key", "=", key)]).unlink()

    def stats(self):
        total = self._hits + self._misses
        return {"hits": self._hits, "misses": self._misses,
                "ratio": round(self._hits / total, 4) if total else 0.0}


class RedisCacheBackend(CacheBackend):
    """Backend Redis (futuro). Interfaz lista; requiere el paquete `redis` y una URL.
    Se mantiene como stub para no acoplar dependencias hasta que se decida usarlo."""

    def __init__(self, url):
        try:
            import redis  # noqa: F401
        except Exception as e:  # pragma: no cover
            raise RuntimeError("Backend Redis no disponible (instala 'redis'): %s" % e)
        import redis
        self._r = redis.Redis.from_url(url)
        self._hits = 0
        self._misses = 0

    def get(self, key):  # pragma: no cover - futuro
        raw = self._r.get(key)
        if raw is None:
            self._misses += 1
            return None
        self._hits += 1
        return json.loads(raw)

    def set(self, key, value, ttl_seconds=None):  # pragma: no cover - futuro
        self._r.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl_seconds)

    def delete(self, key):  # pragma: no cover - futuro
        self._r.delete(key)

    def stats(self):  # pragma: no cover - futuro
        total = self._hits + self._misses
        return {"hits": self._hits, "misses": self._misses,
                "ratio": round(self._hits / total, 4) if total else 0.0}


def get_cache_backend(env, kind: str = None) -> CacheBackend:
    """Factoría: devuelve el backend configurado (`catalog.cache_backend`, default postgres)."""
    kind = kind or env["ir.config_parameter"].sudo().get_param("catalog.cache_backend", "postgres")
    if kind == "redis":
        url = env["ir.config_parameter"].sudo().get_param("catalog.redis_url", "redis://localhost:6379/0")
        return RedisCacheBackend(url)
    return PostgresCacheBackend(env)

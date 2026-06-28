"""Tolerancia a errores, métricas por endpoint y circuit breaker (objetivos #4, #5).
Sin red: se inyecta una sesión falsa con respuestas programadas.
"""
import time

import requests
from odoo.tests.common import TransactionCase

from odoo.addons.distributor_syscom.lib.syscom_connector import SyscomConnector
from odoo.addons.distributor_connector_base.lib.exceptions import (
    RateLimitError, UpstreamUnavailableError, ConnectorError, CircuitOpenError)


class FakeResp:
    def __init__(self, status=200, json_data=None, raise_json=False):
        self.status_code = status
        self._json = json_data if json_data is not None else {}
        self._raise = raise_json
        self.raw = None

    def json(self):
        if self._raise:
            raise ValueError("bad json")
        return self._json


class FakeSession:
    """Devuelve/laza los elementos de `script` en orden (Exception → se lanza)."""
    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls += 1
        item = self.script.pop(0) if self.script else FakeResp(200, {})
        if isinstance(item, Exception):
            raise item
        return item


def make_conn(script, **over):
    secrets = {"token_cache": "tok", "token_expiry": str(time.time() + 10 ** 9),
               "client_id": "x", "client_secret": "y"}
    cfg = {"api_url": "http://fake", "get_secret": secrets.get,
           "set_secret": lambda k, v: secrets.__setitem__(k, v),
           "rate_limit": 100000, "timeout": 1, "circuit_failure_threshold": 3}
    cfg.update(over)
    c = SyscomConnector(cfg)
    c._session = FakeSession(script)
    return c


class TestConnectorResilience(TransactionCase):

    def test_http_429(self):
        c = make_conn([FakeResp(429)])
        with self.assertRaises(RateLimitError):
            c.get_product("1")
        self.assertGreaterEqual(c.metrics["get_product"]["errors"], 1)

    def test_http_500(self):
        c = make_conn([FakeResp(500)])
        with self.assertRaises(UpstreamUnavailableError):
            c.get_product("1")

    def test_timeout(self):
        c = make_conn([requests.Timeout("slow")])
        with self.assertRaises(UpstreamUnavailableError):
            c.get_product("1")

    def test_invalid_json(self):
        c = make_conn([FakeResp(200, raise_json=True)])
        with self.assertRaises(UpstreamUnavailableError):
            c.get_product("1")

    def test_error_payload(self):
        c = make_conn([FakeResp(200, {"error": "product_not_available"})])
        with self.assertRaises(ConnectorError):
            c.get_product("1")

    def test_401_then_ok(self):
        c = make_conn([FakeResp(401), FakeResp(200, {"producto_id": 1, "titulo": "X"})])
        c.authenticate = lambda force=False: "tok"   # evita el OAuth real en el refresh
        np = c.get_product("1")
        self.assertEqual(np.external_ref, "1")
        self.assertEqual(c._session.calls, 2)        # reintentó tras 401

    def test_metrics_per_endpoint(self):
        c = make_conn([FakeResp(200, {"producto_id": 1, "titulo": "X"})])
        c.get_product("1")
        s = c.metrics_summary()["get_product"]
        self.assertEqual(s["count"], 1)
        self.assertGreaterEqual(s["avg_ms"], 0.0)
        self.assertIn("max_ms", s)

    def test_circuit_breaker_opens(self):
        c = make_conn([FakeResp(500), FakeResp(500), FakeResp(500)], circuit_failure_threshold=3)
        for _ in range(3):
            with self.assertRaises(UpstreamUnavailableError):
                c.get_product("1")
        # 4ª llamada: breaker abierto → corta sin pegarle al upstream
        with self.assertRaises(CircuitOpenError):
            c.get_product("1")

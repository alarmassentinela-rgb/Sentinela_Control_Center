"""Pruebas de la librería pura (ejecutadas como TransactionCase para que el filtro
--test-tags de Odoo las recoja; no usan la DB)."""
from odoo.tests.common import TransactionCase

from odoo.addons.distributor_connector_base.lib import (
    version, dto, events, resilience, connector)
from odoo.addons.distributor_connector_base.lib.exceptions import (
    NormalizationError, CircuitOpenError)


class TestVersion(TransactionCase):
    def test_compatible(self):
        self.assertTrue(version.is_compatible("1.0.0", ">=1.0,<2.0"))
        self.assertTrue(version.is_compatible("1.5.3", ">=1.0"))
        self.assertFalse(version.is_compatible("2.0.0", ">=1.0,<2.0"))
        self.assertFalse(version.is_compatible("0.9.0", ">=1.0"))
        self.assertTrue(version.is_compatible("1.0.0", ""))


class TestDTO(TransactionCase):
    def test_valid(self):
        p = dto.NormalizedProduct(backend_key="syscom", external_ref="377", name="Resistor")
        self.assertEqual(p.to_dict()["external_ref"], "377")
        self.assertEqual(p.price.currency, "USD")

    def test_invalid(self):
        with self.assertRaises(NormalizationError):
            dto.NormalizedProduct(backend_key="", external_ref="1", name="x")
        with self.assertRaises(NormalizationError):
            dto.NormalizedProduct(backend_key="s", external_ref="", name="x")


class TestEvents(TransactionCase):
    def test_pubsub(self):
        bus = events.EventBus()
        got = []
        bus.subscribe(events.EVT_PRICE_UPDATED, lambda e: got.append(e))
        n = bus.publish(events.Event(name=events.EVT_PRICE_UPDATED, backend_key="syscom"))
        self.assertEqual(n, 1)
        self.assertEqual(got[0].backend_key, "syscom")

    def test_unknown_raises(self):
        bus = events.EventBus()
        with self.assertRaises(ValueError):
            bus.publish(events.Event(name="Nope"))

    def test_handler_isolation(self):
        bus = events.EventBus()
        ok = []
        bus.subscribe(events.EVT_CACHE_HIT, lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
        bus.subscribe(events.EVT_CACHE_HIT, lambda e: ok.append(1))
        delivered = bus.publish(events.Event(name=events.EVT_CACHE_HIT))
        self.assertEqual(ok, [1])           # el 2.º corre aunque el 1.º falle
        self.assertEqual(delivered, 1)


class TestResilience(TransactionCase):
    def test_backoff(self):
        self.assertEqual(resilience.backoff_delays(3, base=1.0, jitter=False), [1.0, 2.0, 4.0])
        self.assertEqual(resilience.backoff_delays(0), [])

    def test_circuit_breaker(self):
        t = [0.0]
        cb = resilience.CircuitBreaker(failure_threshold=2, recovery_timeout=10, clock=lambda: t[0])

        def boom():
            raise RuntimeError("x")

        for _ in range(2):
            with self.assertRaises(RuntimeError):
                cb.call(boom)
        self.assertEqual(cb.state, cb.OPEN)
        with self.assertRaises(CircuitOpenError):
            cb.call(lambda: 1)
        t[0] = 11
        self.assertEqual(cb.state, cb.HALF_OPEN)
        self.assertEqual(cb.call(lambda: 42), 42)
        self.assertEqual(cb.state, cb.CLOSED)

    def test_rate_limiter(self):
        clk = [0.0]
        slept = []

        def sleep(s):
            slept.append(s)
            clk[0] += s

        rl = resilience.RateLimiter(rate_per_min=60, clock=lambda: clk[0], sleep=sleep)
        for _ in range(60):
            self.assertEqual(rl.acquire(), 0.0)   # capacidad inicial, sin espera
        waited = rl.acquire()                      # token 61 → espera ~1s
        self.assertGreater(waited, 0.0)
        self.assertTrue(slept)


class TestRegistry(TransactionCase):
    def test_register_and_resolve(self):
        @connector.register_connector("dummy_unit")
        class Dummy(connector.DistributorConnector):
            version = "1.0.0"

            def authenticate(self):
                return "tok"

            def search(self, query, filters=None, page=1):
                return []

            def get_product(self, ref):
                return dto.NormalizedProduct(backend_key="dummy_unit", external_ref=ref, name="x")

            def get_price_stock(self, refs):
                return {}

            def normalize(self, raw):
                return dto.NormalizedProduct(backend_key="dummy_unit", external_ref="1", name="x")

        self.assertIn("dummy_unit", connector.available_connectors())
        cls = connector.get_connector_class("dummy_unit")
        self.assertEqual(cls({}).authenticate(), "tok")

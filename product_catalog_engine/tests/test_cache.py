"""Caché reemplazable (principio #6): backend Postgres + factoría por parámetro."""
from odoo.tests.common import TransactionCase

from odoo.addons.product_catalog_engine.lib import cache


class TestCache(TransactionCase):
    def test_postgres_backend(self):
        c = cache.get_cache_backend(self.env)
        self.assertIsInstance(c, cache.PostgresCacheBackend)
        self.assertIsNone(c.get("k1"))            # miss
        c.set("k1", {"a": 1})
        self.assertEqual(c.get("k1"), {"a": 1})   # hit
        st = c.stats()
        self.assertEqual(st["hits"], 1)
        self.assertEqual(st["misses"], 1)
        self.assertIn("ratio", st)
        c.delete("k1")
        self.assertIsNone(c.get("k1"))

    def test_ttl_expiry(self):
        c = cache.get_cache_backend(self.env)
        c.set("k2", 1, ttl_seconds=-1)            # ya expirado
        self.assertIsNone(c.get("k2"))

    def test_factory_replaceable(self):
        self.env["ir.config_parameter"].sudo().set_param("catalog.cache_backend", "postgres")
        self.assertIsInstance(cache.get_cache_backend(self.env), cache.PostgresCacheBackend)

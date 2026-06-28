"""Catalog Public Interface: capa de servicios + API key/rate-limit/idempotencia + OpenAPI.
(Los endpoints HTTP se validan en vivo con curl/CLI tras desplegar; aquí lo unitario.)"""
from odoo import fields
from odoo.tests.common import TransactionCase

from odoo.addons.distributor_connector_base.lib import connector as conn
from odoo.addons.distributor_connector_base.lib import dto
from odoo.addons.product_catalog_engine.lib import api_service, openapi_spec as oas


@conn.register_connector("api_test")
class _ApiConnector(conn.DistributorConnector):
    version = "1.0.0"

    def authenticate(self):
        return "t"

    def search(self, query, filters=None, page=1):
        return []

    def get_product(self, ref):
        return dto.NormalizedProduct(backend_key="api_test", external_ref=ref, name="x")

    def get_price_stock(self, refs):
        return {r: {"price": {"cost": 1.0}, "stock": {"total": 3}} for r in refs}

    def normalize(self, raw):
        return dto.NormalizedProduct(backend_key="api_test", external_ref="1", name="x")


class TestCatalogApi(TransactionCase):
    def setUp(self):
        super().setUp()
        partner = self.env["res.partner"].search([], limit=1)
        self.bk = self.env["distributor.backend"].create(
            {"name": "APITest", "connector_key": "api_test", "partner_id": partner.id})
        self.Item = self.env["distributor.catalog.item"]
        self.it = self.Item.create({"backend_id": self.bk.id, "distributor_product_id": "API1",
                                    "name": "Cámara API", "brand": "HIK", "sat_code": "4617",
                                    "price_list": 100.0, "stock_total": 9})
        self.svc = api_service.CatalogApiService(self.env)

    def test_search_paginated(self):
        for i in range(5):
            self.Item.create({"backend_id": self.bk.id, "distributor_product_id": "P%d" % i,
                              "name": "Item %d" % i, "brand": "HIK"})
        res = self.svc.search(filters={"brand": "HIK"}, page=1, page_size=3, sort="name")
        self.assertEqual(res["pagination"]["page_size"], 3)
        self.assertEqual(len(res["data"]), 3)
        self.assertGreaterEqual(res["pagination"]["total"], 6)

    def test_search_by_q(self):
        res = self.svc.search(q="Cámara")
        self.assertTrue(any(d["distributor_product_id"] == "API1" for d in res["data"]))

    def test_get_product_refresh_on_stale(self):
        self.it._mark_synced("stock")
        self.it.stock_expires_at = fields.Datetime.subtract(fields.Datetime.now(), minutes=1)
        dto_ = self.svc.get_product("API1")
        self.assertEqual(dto_["stock"]["total"], 3)        # refrescó on-demand (vencido)
        self.assertGreaterEqual(self.it.hit_count, 1)      # registró consulta

    def test_promote_via_service(self):
        res = self.svc.promote("API1")
        self.assertTrue(res["product_master_id"])
        self.assertTrue(res["is_catalog_managed"])

    def test_health(self):
        h = self.svc.health()
        self.assertEqual(h["status"], "ok")
        self.assertIn("engine_version", h)

    def test_api_key_auth_scope_ratelimit(self):
        k = self.env["catalog.api.key"].create(
            {"name": "k", "scopes": "read", "rate_limit_per_min": 2})
        self.assertEqual(self.env["catalog.api.key"].authenticate(k.key), k)
        self.assertFalse(self.env["catalog.api.key"].authenticate("nope"))
        self.assertTrue(k.has_scope("read"))
        self.assertFalse(k.has_scope("promote"))
        a1 = k.consume(); a2 = k.consume(); a3 = k.consume()
        self.assertTrue(a1[0] and a2[0])
        self.assertFalse(a3[0])                            # 3ª excede límite=2

    def test_idempotency(self):
        I = self.env["catalog.api.idempotency"]
        I.store("idem-1", "promote", 200, '{"ok": true}')
        self.assertTrue(I.fetch("idem-1"))
        self.assertFalse(I.fetch("nope"))

    def test_openapi_and_schema(self):
        spec = oas.build_openapi()
        self.assertEqual(spec["openapi"], "3.0.3")
        self.assertIn("/products", spec["paths"])
        self.assertIn("Product", spec["components"]["schemas"])
        self.assertEqual(oas.product_json_schema()["title"], "CatalogProduct")

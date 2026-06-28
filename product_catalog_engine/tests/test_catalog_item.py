"""Índice: identidad única, code_norm, búsqueda multi-campo, promoción auditada."""
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.distributor_connector_base.lib import connector as conn
from odoo.addons.distributor_connector_base.lib import dto


@conn.register_connector("engine_utest")
class _EngineTestConnector(conn.DistributorConnector):
    version = "1.0.0"

    def authenticate(self):
        return "t"

    def search(self, query, filters=None, page=1):
        return []

    def get_product(self, ref):
        return dto.NormalizedProduct(backend_key="engine_utest", external_ref=ref, name="x")

    def get_price_stock(self, refs):
        return {}

    def normalize(self, raw):
        return dto.NormalizedProduct(backend_key="engine_utest", external_ref="1", name="x")


class TestCatalogItem(TransactionCase):
    def setUp(self):
        super().setUp()
        self.backend = self.env["distributor.backend"].create({
            "name": "EngineUTest", "connector_key": "engine_utest"})
        self.Item = self.env["distributor.catalog.item"]

    def _item(self, **kw):
        vals = dict(backend_id=self.backend.id, distributor_product_id="P1",
                    name="Cámara Domo IP", distributor_sku="PRO-CAT-5E",
                    manufacturer_sku="DS-2CD", barcode="7501234567890", sat_code="46171610",
                    brand="HIKVISION")
        vals.update(kw)
        return self.Item.create(vals)

    def test_code_norm(self):
        it = self._item()
        self.assertEqual(it.code_norm, "procat5eds2cdp1")     # sku+msku+pid, alnum lower

    def test_identity_is_not_sku(self):
        """La identidad del índice es (backend, distributor_product_id), NO el SKU."""
        it = self._item()
        self.assertEqual(it.distributor_product_id, "P1")
        self.assertFalse(it.product_tmpl_id)                  # aún no es producto maestro

    @mute_logger("odoo.sql_db")
    def test_unique_identity(self):
        self._item()
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._item()                                  # mismo backend+product_id
                self.env.flush_all()

    def test_search_multifield(self):
        self._item()
        self.assertTrue(self.Item.search_index("domo"))            # name
        self.assertTrue(self.Item.search_index("HIKVISION"))       # brand
        self.assertTrue(self.Item.search_index("46171610"))        # SAT
        self.assertTrue(self.Item.search_index("7501234567890"))   # barcode
        self.assertTrue(self.Item.search_index("DS-2CD"))          # manufacturer sku
        self.assertTrue(self.Item.search_index("procat5e"))        # code_norm (sin guiones)

    def test_link_master_audits(self):
        it = self._item()
        # Crea su propio producto (reproducible en BD limpia sin demo; guarda NOT-NULL sale/purchase).
        tvals = {"name": "Master Test", "type": "consu"}
        Tmpl = self.env["product.template"]
        for w in ("sale_line_warn", "purchase_line_warn"):
            if w in Tmpl._fields:
                tvals[w] = "no-message"
        tmpl = Tmpl.create(tvals)
        it.link_master(tmpl, source="wizard")
        self.assertEqual(it.product_tmpl_id, tmpl)
        log = self.env["catalog.audit.log"].search(
            [("action", "=", "promote"), ("res_ref", "=", "P1")], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.new_value, str(tmpl.id))

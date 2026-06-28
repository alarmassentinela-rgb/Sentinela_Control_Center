"""Scheduler inteligente D3d: frescura, políticas, refresco por tier (sin full scan),
eventos, prioridades, calidad."""
from odoo import fields
from odoo.tests.common import TransactionCase

from odoo.addons.distributor_connector_base.lib import connector as conn
from odoo.addons.distributor_connector_base.lib import dto
from odoo.addons.distributor_connector_base.lib import events as ev


@conn.register_connector("sched_test")
class _SchedConnector(conn.DistributorConnector):
    version = "1.0.0"
    PRICE = 10.0
    STOCK = 5

    def authenticate(self):
        return "t"

    def search(self, query, filters=None, page=1):
        return []

    def get_product(self, ref):
        return dto.NormalizedProduct(backend_key="sched_test", external_ref=ref,
                                     name="P %s" % ref, description="desc %s" % ref,
                                     images=["http://x/1.png"], documents=[])

    def get_price_stock(self, refs):
        return {r: {"price": {"cost": self.PRICE, "list": self.PRICE + 5},
                    "stock": {"total": self.STOCK}} for r in refs}

    def normalize(self, raw):
        return dto.NormalizedProduct(backend_key="sched_test", external_ref="1", name="x")


class TestScheduler(TransactionCase):
    def setUp(self):
        super().setUp()
        self.bk = self.env["distributor.backend"].create(
            {"name": "Sched", "connector_key": "sched_test"})
        self.Item = self.env["distributor.catalog.item"]

    def _item(self, ref, **kw):
        vals = dict(backend_id=self.bk.id, distributor_product_id=ref, name="N %s" % ref,
                    price_cost=99.0, stock_total=99)
        vals.update(kw)
        return self.Item.create(vals)

    def test_policy_ttl(self):
        P = self.env["catalog.sync.policy"]
        self.assertEqual(P._ttl("price"), 1440)
        self.assertEqual(P._ttl("stock"), 30)
        self.assertEqual(P._ttl("enrichment"), 43200)

    def test_freshness_lifecycle(self):
        it = self._item("A")
        self.assertEqual(it.freshness_status, "never")
        it._mark_synced("price"); it._mark_synced("stock"); it._mark_synced("enrichment")
        self.assertEqual(it.freshness_status, "fresh")
        self.assertTrue(it.price_expires_at and it.stock_expires_at)
        # forzar expiración de stock
        it.stock_expires_at = fields.Datetime.subtract(fields.Datetime.now(), minutes=1)
        self.assertTrue(it._is_due("stock"))
        self.assertEqual(it.freshness_status, "expired")

    def test_refresh_updates_and_emits(self):
        it = self._item("B")
        n_before = self.env["catalog.event"].search_count([("name", "=", ev.EVT_PRICE_CHANGED)])
        it.refresh(["price", "stock", "enrichment"])
        self.assertEqual(it.price_cost, 10.0)        # del conector
        self.assertEqual(it.stock_total, 5)
        self.assertTrue(it.price_synced_at and it.enrichment_synced_at)
        n_after = self.env["catalog.event"].search_count([("name", "=", ev.EVT_PRICE_CHANGED)])
        self.assertGreater(n_after, n_before)         # emitió PriceChanged

    def test_cron_refreshes_only_due_by_tier(self):
        """El cron refresca SOLO lo vencido (no recorre todo)."""
        due = self._item("DUE")                       # stock nunca sincronizado → vencido
        fresh = self._item("FRESH")
        fresh._mark_synced("stock")                   # vigente → NO debe tocarse
        self.Item._cron_refresh_stock()
        self.assertEqual(due.stock_total, 5)          # refrescado
        self.assertEqual(fresh.stock_total, 99)       # intacto (no se recorrió)

    def test_recompute_tiers(self):
        fav = self._item("FAV", is_favorite=True)
        hot = self._item("HOT", hit_count=10)
        cold = self._item("COLD")
        self.Item._cron_recompute_tiers()
        self.assertEqual(fav.sync_tier, "2")
        self.assertEqual(hot.sync_tier, "3")
        self.assertEqual(cold.sync_tier, "4")

    def test_register_hit(self):
        it = self._item("H")
        it.register_hit(); it.register_hit()
        self.assertEqual(it.hit_count, 2)
        self.assertTrue(it.last_hit_at)

    def test_quality_detection(self):
        self._item("Q1")                              # never synced
        q = self.Item._cron_detect_quality()
        self.assertGreaterEqual(q["never"], 1)
        self.assertIn("total", q)



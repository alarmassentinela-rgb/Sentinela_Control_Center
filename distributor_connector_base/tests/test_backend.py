"""Pruebas de integración Odoo: backend, secretos, rotación, conector, run/evento/auditoría."""
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

from odoo.addons.distributor_connector_base.lib import connector as conn
from odoo.addons.distributor_connector_base.lib import dto
from odoo.addons.distributor_connector_base.lib import events as evt
from odoo.addons.distributor_connector_base.lib import version as ver


@conn.register_connector("utest")
class _UTestConnector(conn.DistributorConnector):
    version = "1.0.0"

    def authenticate(self):
        return "ok"

    def search(self, query, filters=None, page=1):
        return []

    def get_product(self, ref):
        return dto.NormalizedProduct(backend_key="utest", external_ref=ref, name="x")

    def get_price_stock(self, refs):
        return {}

    def normalize(self, raw):
        return dto.NormalizedProduct(backend_key="utest", external_ref="1", name="x")


class TestBackend(TransactionCase):
    def setUp(self):
        super().setUp()
        self.backend = self.env["distributor.backend"].create({
            "name": "UTest", "connector_key": "utest", "api_url": "http://x"})

    def test_secret_set_get(self):
        self.backend.set_secret("k", "v")
        self.assertEqual(self.backend.get_secret("k"), "v")

    def test_rotate_credentials(self):
        self.backend.set_secret("token_cache", "abc")
        self.backend.rotate_credentials()
        self.assertFalse(self.backend.get_secret("token_cache"))
        self.assertTrue(self.backend.credential_rotated_on)

    def test_versions_computed(self):
        self.assertEqual(self.backend.engine_version, ver.ENGINE_VERSION)
        self.assertEqual(self.backend.connector_version, "1.0.0")
        self.assertTrue(self.backend.connector_compatible)

    def test_get_connector(self):
        c = self.backend.get_connector()
        self.assertEqual(c.authenticate(), "ok")

    def test_run_metrics(self):
        run = self.env["catalog.run"].create({"operation": "sync", "backend_id": self.backend.id})
        run.log_metric("api_call", 123.0, ref="r1")
        run.finish("done", message="ok")
        self.assertEqual(run.state, "done")
        self.assertTrue(run.duration_ms >= 0)
        self.assertEqual(len(run.metric_ids), 1)

    def test_event_emit(self):
        ev = self.env["catalog.event"].emit(
            evt.EVT_CATALOG_SYNCED, backend_key="utest", payload={"n": 5})
        self.assertEqual(ev.name, evt.EVT_CATALOG_SYNCED)
        self.assertIn("5", ev.payload)

    def test_audit_append_only(self):
        log = self.env["catalog.audit.log"].record(
            "price", model="product.template", res_ref="1", old_value=1, new_value=2)
        self.assertEqual(log.new_value, "2")
        with self.assertRaises(UserError):
            log.write({"message": "no"})

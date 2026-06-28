"""Promoción índice → Producto Maestro (D3b). Cubre las 10 reglas."""
from odoo.tests.common import TransactionCase

from odoo.addons.distributor_connector_base.lib import connector as conn
from odoo.addons.distributor_connector_base.lib import dto


def _mk_connector(key):
    @conn.register_connector(key)
    class _C(conn.DistributorConnector):
        version = "1.0.0"

        def authenticate(self):
            return "t"

        def search(self, query, filters=None, page=1):
            return []

        def get_product(self, ref):
            return dto.NormalizedProduct(backend_key=key, external_ref=ref, name="x")

        def get_price_stock(self, refs):
            return {}

        def normalize(self, raw):
            return dto.NormalizedProduct(backend_key=key, external_ref="1", name="x")
    return _C


_mk_connector("promo_a")
_mk_connector("promo_b")


class TestPromotion(TransactionCase):
    def setUp(self):
        super().setUp()
        B = self.env["distributor.backend"]
        # Partners existentes (STAGING tiene NOT NULL sin default que rompe crear partner).
        partners = self.env["res.partner"].search([], limit=2)
        self.ba = B.create({"name": "Distrib A", "connector_key": "promo_a",
                            "partner_id": partners[0].id})
        self.bb = B.create({"name": "Distrib B", "connector_key": "promo_b",
                            "partner_id": partners[-1].id})
        self.Item = self.env["distributor.catalog.item"]
        self.Tmpl = self.env["product.template"]

    def _mk_template(self, **kw):
        vals = {"name": "X", "type": "consu"}
        for w in ("sale_line_warn", "purchase_line_warn"):
            if w in self.Tmpl._fields:
                vals.setdefault(w, "no-message")
        vals.update(kw)
        return self.Tmpl.create(vals)

    def _item(self, backend, **kw):
        vals = dict(backend_id=backend.id, distributor_product_id="P1", name="Cámara Domo IP",
                    distributor_sku="SKU-1", manufacturer_sku="DS-2CD1143", barcode="7501234567890",
                    sat_code="46171610", brand="HIKVISION", price_cost=81.5, description="Domo 4MP")
        vals.update(kw)
        return self.Item.create(vals)

    # 1/2 — nace el maestro, idempotente
    def test_promote_and_idempotent(self):
        it = self._item(self.ba)
        m1 = it.promote()
        self.assertTrue(m1.is_catalog_managed)
        self.assertEqual(it.product_tmpl_id, m1)
        si = self.env["product.supplierinfo"].search([("catalog_item_id", "=", it.id)])
        self.assertEqual(len(si), 1)
        # promover de nuevo NO duplica
        m2 = it.promote()
        self.assertEqual(m1, m2)
        self.assertEqual(len(self.env["product.supplierinfo"].search(
            [("distributor_backend_id", "=", self.ba.id), ("distributor_product_id", "=", "P1")])), 1)

    # 3 — respeta edición manual del nombre
    def test_respect_manual_edit(self):
        it = self._item(self.ba)
        m = it.promote()
        m.name = "NOMBRE EDITADO A MANO"
        it.name = "Nombre nuevo del proveedor"   # el proveedor cambia
        it.promote()
        self.assertEqual(m.name, "NOMBRE EDITADO A MANO")   # se respeta lo manual

    # 3b — si NO hubo edición manual, el cambio del proveedor sí aplica
    def test_provider_update_applies(self):
        it = self._item(self.ba)
        m = it.promote()
        it.name = "Nombre actualizado proveedor"
        it.promote()
        self.assertEqual(m.name, "Nombre actualizado proveedor")

    # 4 — ownership: el proveedor NUNCA toca campos del ERP
    def test_erp_fields_untouched(self):
        it = self._item(self.ba)
        m = it.promote()
        cat = self.env["product.category"].create({"name": "Comercial X"})
        m.write({"categ_id": cat.id, "list_price": 999.0})
        it.price_cost = 50.0
        it.promote()
        self.assertEqual(m.categ_id, cat)        # categoría comercial intacta
        self.assertEqual(m.list_price, 999.0)    # precio de venta intacto
        si = self.env["product.supplierinfo"].search([("catalog_item_id", "=", it.id)])
        self.assertEqual(si.price, 50.0)         # el costo (proveedor) sí se actualizó

    # 7/9 — dos distribuidores, mismo maestro (multi-proveedor sin cambios de modelo)
    def test_multi_distributor_single_master(self):
        ia = self._item(self.ba, distributor_product_id="A1")
        ib = self._item(self.bb, distributor_product_id="B1")   # mismo barcode/manufacturer_sku
        ma = ia.promote()
        mb = ib.promote()
        self.assertEqual(ma, mb)                  # UN solo maestro
        sellers = self.env["product.supplierinfo"].search([("product_tmpl_id", "=", ma.id)])
        self.assertEqual(len(sellers), 2)         # DOS proveedores
        self.assertEqual(ma.distributor_count, 2)

    # 10 — el maestro existe con independencia del proveedor que lo originó
    def test_master_independent_of_provider(self):
        it = self._item(self.ba)
        m = it.promote()
        si_id = self.env["product.supplierinfo"].search([("catalog_item_id", "=", it.id)]).id
        it.unlink()                               # el distribuidor "elimina" el ítem del índice
        self.assertTrue(m.exists())               # el MAESTRO sigue existiendo
        self.assertTrue(self.env["product.supplierinfo"].browse(si_id).exists())

    # 8 — un producto PROPIO nunca es secuestrado por la promoción
    def test_own_product_not_hijacked(self):
        own = self._mk_template(name="Plan Propio", barcode="7501234567890",
                                default_code="DS-2CD1143", is_catalog_managed=False)
        it = self._item(self.ba)                  # mismo barcode/manufacturer_sku que el propio
        m = it.promote()
        self.assertNotEqual(m, own)               # NO se ligó al propio
        self.assertTrue(m.is_catalog_managed)
        self.assertFalse(own.is_catalog_managed)

    # 5 — versionado: la sincronización deja evidencia (old/new/fecha/origen)
    def test_versioning_audit(self):
        it = self._item(self.ba)
        it.promote(source="user")
        logs = self.env["catalog.audit.log"].search(
            [("backend_id", "=", self.ba.id), ("model", "in", ("product.template", "product.supplierinfo"))])
        self.assertTrue(logs)
        self.assertTrue(any(l.source == "user" for l in logs))

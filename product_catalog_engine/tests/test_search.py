"""Búsqueda: normalización de código y construcción de dominio (principio #4)."""
from odoo.tests.common import TransactionCase

from odoo.addons.product_catalog_engine.lib import search


class TestSearch(TransactionCase):
    def test_normalize_code(self):
        self.assertEqual(search.normalize_code("PRO-CAT-5E"), "procat5e")
        self.assertEqual(search.normalize_code("DS 2CD/1143"), "ds2cd1143")
        self.assertEqual(search.normalize_code(None), "")

    def test_build_domain(self):
        d = search.build_search_domain("domo")
        fields_in = {t[0] for t in d if isinstance(t, tuple)}
        self.assertIn("name", fields_in)
        self.assertIn("sat_code", fields_in)
        self.assertIn("barcode", fields_in)
        self.assertIn("code_norm", fields_in)
        self.assertEqual(search.build_search_domain(""), [])

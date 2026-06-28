"""Calidad de datos: advertencias sin detener la sincronización (objetivo #6)."""
import json
import os

from odoo.tests.common import TransactionCase

from odoo.addons.distributor_syscom.lib import mapping, quality
from odoo.addons.distributor_connector_base.lib.dto import (
    NormalizedProduct, NormalizedPrice)

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    with open(os.path.join(FIX, name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


class TestQuality(TransactionCase):

    def test_clean_product_no_warnings(self):
        np = mapping.normalize(load("camara_ip"))
        warns = quality.check(np)
        self.assertNotIn(quality.W_MISSING_SAT, warns)
        self.assertNotIn(quality.W_EMPTY_CATEGORY, warns)
        self.assertNotIn(quality.W_NO_BRAND, warns)

    def test_dirty_product_warnings(self):
        np = NormalizedProduct(
            backend_key="syscom", external_ref="X", name="malo",
            brand=None, category_path=[], sat_key=None,
            images=["ftp://no-http/img.png"], price=NormalizedPrice())
        warns = quality.check(np)
        self.assertIn(quality.W_MISSING_SAT, warns)
        self.assertIn(quality.W_EMPTY_CATEGORY, warns)
        self.assertIn(quality.W_NO_BRAND, warns)
        self.assertIn(quality.W_BROKEN_IMAGE, warns)
        self.assertIn(quality.W_NO_PRICE, warns)

    def test_duplicates(self):
        a = mapping.normalize(load("switch"))
        dups = quality.find_duplicates([a, a])
        self.assertEqual(dups, [a.external_ref])

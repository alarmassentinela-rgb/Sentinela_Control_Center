"""Normalización con FIXTURES REALES de la API Syscom (objetivos #1, #2, #3)."""
import json
import os

from odoo.tests.common import TransactionCase

from odoo.addons.distributor_syscom.lib import mapping
from odoo.addons.distributor_connector_base.lib.exceptions import NormalizationError

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    with open(os.path.join(FIX, name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


class TestMapping(TransactionCase):

    DETAIL_FIXTURES = ["camara_ip", "nvr", "switch", "cable", "accesorio",
                       "software", "servicio", "sin_imagen"]

    def test_all_detail_fixtures_normalize(self):
        """Todos los tipos de producto reales se normalizan sin romper."""
        for name in self.DETAIL_FIXTURES:
            np = mapping.normalize(load(name))
            self.assertTrue(np.external_ref, "%s sin external_ref" % name)
            self.assertTrue(np.name, "%s sin name" % name)
            self.assertEqual(np.price.currency, "USD")

    def test_camara_ip_full_mapping(self):
        np = mapping.normalize(load("camara_ip"))
        self.assertEqual(np.external_ref, "221944")
        self.assertTrue(np.brand)
        self.assertEqual(np.category_path[0], "Videovigilancia")        # nivel 1
        self.assertGreaterEqual(len(np.images), 5)                       # galería
        self.assertTrue(all(u.startswith("http") for u in np.images))
        self.assertTrue(np.documents and np.documents[0].url.startswith("http"))
        self.assertTrue(np.sat_key)
        self.assertEqual(np.sat_unit, "H87")
        self.assertTrue(np.warranty)                                     # garantía
        self.assertIsNotNone(np.price.map)                              # precio MAP
        self.assertIn("alto", np.dimensions)
        self.assertTrue(np.attributes)                                  # características
        self.assertEqual(np.raw["_unknown_keys"], [])                   # 100% de la API mapeada

    def test_sin_imagen_uses_portada_or_empty(self):
        np = mapping.normalize(load("sin_imagen"))
        self.assertTrue(np.external_ref)
        # producto sin galería: lista de imágenes vacía o con portada, nunca error
        self.assertIsInstance(np.images, list)

    def test_error_payload_raises(self):
        raw = load("sin_existencia")  # {'error': 'product_not_available'}
        self.assertTrue(mapping.is_error_payload(raw))
        with self.assertRaises(NormalizationError):
            mapping.normalize(raw)

    def test_forward_compatibility(self):
        """Un campo NUEVO de Syscom no rompe; se registra en _unknown_keys."""
        raw = dict(load("switch"))
        raw["campo_futuro_inexistente"] = {"algo": 1}
        np = mapping.normalize(raw)
        self.assertIn("campo_futuro_inexistente", np.raw["_unknown_keys"])

    def test_null_tolerance(self):
        """Nulos/strings vacíos no rompen el parseo."""
        raw = {"producto_id": 1, "titulo": "X", "precios": None, "existencia": None,
               "imagenes": None, "recursos": None, "categorias": None,
               "unidad_de_medida": None, "peso": "", "sat_key": None}
        np = mapping.normalize(raw)
        self.assertEqual(np.external_ref, "1")
        self.assertIsNone(np.price.cost)
        self.assertEqual(np.stock.total, 0)
        self.assertEqual(np.images, [])

    def test_embedding_text(self):
        np = mapping.normalize(load("camara_ip"))
        text = mapping.to_embedding_text(np)
        self.assertIn(np.name, text)
        self.assertIn("Videovigilancia", text)

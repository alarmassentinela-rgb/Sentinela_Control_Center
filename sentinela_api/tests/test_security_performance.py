# -*- coding: utf-8 -*-
"""WS-2 — Rendimiento de las record rules con volumen representativo.

Verifica que el filtrado por record rule (aislamiento por partner) NO degrada
de forma patologica las consultas del portal al crecer el volumen de datos.

Es un smoke de rendimiento: crea N registros repartidos en M clientes y mide el
tiempo de una busqueda hecha COMO el usuario portal. La validacion contra el
volumen real de produccion se hace ademas manualmente en STAGING (checklist).
"""
import base64
import time

from odoo.tests.common import TransactionCase, tagged

PARTNERS = 20          # clientes
DOCS_PER_PARTNER = 10  # registros por cliente  -> 200 registros
MAX_SECONDS = 5.0      # cota generosa para detectar regresiones catastroficas


@tagged('post_install', '-at_install', 'sentinela_api', 'security', 'perf')
class TestRecordRulePerformance(TransactionCase):

    def test_portal_search_scales(self):
        Partner = self.env['res.partner']
        Doc = self.env['sentinela.sign.document'].sudo()
        pdf = base64.b64encode(b'%PDF-1.4 perf')

        partners = Partner.create([{'name': 'Perf Cliente %d' % i} for i in range(PARTNERS)])
        for p in partners:
            Doc.create([{'partner_id': p.id, 'file': pdf} for _ in range(DOCS_PER_PARTNER)])

        target = partners[0]
        portal_user = self.env['res.users']._coc_ensure_portal_user(target)

        SignAsUser = self.env['sentinela.sign.document'].with_user(portal_user)
        t0 = time.perf_counter()
        docs = SignAsUser.search([])
        elapsed = time.perf_counter() - t0

        # Correccion: solo ve los suyos (aislamiento) ...
        self.assertEqual(len(docs), DOCS_PER_PARTNER,
                         "El portal debe ver solo los registros de su cliente")
        self.assertTrue(all(d.partner_id == target for d in docs))
        # ... y en tiempo razonable (smoke de rendimiento).
        self.assertLess(elapsed, MAX_SECONDS,
                        "Busqueda con record rule tardo %.3fs (>%.1fs)" % (elapsed, MAX_SECONDS))
        _ = elapsed  # el valor real se registra al correr con --test-tags perf en STAGING

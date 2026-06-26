# -*- coding: utf-8 -*-
"""Smoke test del esqueleto sentinela_api (WS-7).

Verifica que el modulo carga y que el serializador base funciona.
Los tests de seguridad (aislamiento por partner, TC-S1..S4) se agregan en WS-2.
"""
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.sentinela_api.lib.serializers import serialize_partner


@tagged('post_install', '-at_install', 'sentinela_api')
class TestApiSmoke(TransactionCase):

    def test_serialize_partner(self):
        partner = self.env['res.partner'].create({'name': 'COC Test'})
        data = serialize_partner(partner)
        self.assertEqual(data['name'], 'COC Test')
        self.assertIn('commercial_partner_id', data)
        self.assertEqual(data['commercial_partner_id'], partner.commercial_partner_id.id)

# -*- coding: utf-8 -*-
"""WS-2 — Pruebas de aislamiento de datos del Portal COC.

Objetivo: garantizar que un cliente NO pueda acceder, directa o indirectamente,
a informacion de otro cliente, aunque el Gateway o un endpoint tuvieran un bug.
Las record rules de Odoo son la PRIMERA linea de defensa.

Cobertura:
- Positivos: el cliente ve SUS registros.
- Negativos / aislamiento: el cliente NO ve registros de otro.
- IDOR (Insecure Direct Object Reference): acceso directo por ID ajeno -> AccessError.
- Broken Access Control: escritura/borrado bloqueados (ACL read-only).
- Estructural: existen record rules y ACL read-only para todos los modelos expuestos.

Nota: las pruebas funcionales se anclan en sentinela.sign.document (modelo simple,
creable con minimos campos). Las estructurales cubren los 6 modelos expuestos.
Al crear el endpoint de cada modelo se anaden pruebas funcionales con su fixture.
"""
import base64

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

EXPOSED_MODELS = [
    'sentinela.subscription',
    'sentinela.alarm.event',
    'sentinela.monitoring.device',
    'sentinela.fsm.order',
    'sentinela.sign.document',
    'account.move',
]
# Modelos con ACL propia read-only del grupo COC (account.move/sign.document se
# heredan de group_portal, no se asertan aqui).
ACL_READONLY_MODELS = [
    'sentinela.subscription',
    'sentinela.alarm.event',
    'sentinela.monitoring.device',
    'sentinela.fsm.order',
]


@tagged('post_install', '-at_install', 'sentinela_api', 'security')
class TestPortalIsolation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.partner_a = Partner.create({'name': 'Cliente A COC'})
        cls.partner_b = Partner.create({'name': 'Cliente B COC'})

        Users = cls.env['res.users']
        cls.user_a = Users._coc_ensure_portal_user(cls.partner_a)
        cls.user_b = Users._coc_ensure_portal_user(cls.partner_b)

        pdf = base64.b64encode(b'%PDF-1.4 test')
        Doc = cls.env['sentinela.sign.document'].sudo()
        cls.doc_a = Doc.create({'partner_id': cls.partner_a.id, 'file': pdf})
        cls.doc_b = Doc.create({'partner_id': cls.partner_b.id, 'file': pdf})

    # ---- Usuario portal lazy ----
    def test_lazy_user_creation_and_groups(self):
        self.assertTrue(self.user_a.share, "El usuario portal debe ser de tipo 'share'")
        self.assertTrue(self.user_a.has_group('base.group_portal'))
        self.assertTrue(self.user_a.has_group('sentinela_api.group_coc_portal'))
        self.assertEqual(self.user_a.partner_id, self.partner_a)

    def test_lazy_user_is_idempotent(self):
        again = self.env['res.users']._coc_ensure_portal_user(self.partner_a)
        self.assertEqual(again, self.user_a, "No debe crear un segundo usuario portal")

    # ---- Positivo: ve lo suyo ----
    def test_positive_sees_own(self):
        docs = self.env['sentinela.sign.document'].with_user(self.user_a).search([])
        self.assertIn(self.doc_a, docs)
        self.assertNotIn(self.doc_b, docs)

    # ---- Negativo: no ve lo ajeno via search ----
    def test_negative_cross_search_hidden(self):
        seen = self.env['sentinela.sign.document'].with_user(self.user_a).search(
            [('id', '=', self.doc_b.id)]
        )
        self.assertFalse(seen, "El cliente A NO debe poder listar documentos de B")

    # ---- IDOR: acceso directo por ID ajeno ----
    def test_idor_direct_browse_read_denied(self):
        with self.assertRaises(AccessError):
            self.env['sentinela.sign.document'].with_user(self.user_a).browse(
                self.doc_b.id
            ).read(['partner_id'])

    # ---- Broken Access Control: sin escritura/borrado ----
    def test_bac_write_denied_even_on_own(self):
        with self.assertRaises(AccessError):
            self.env['sentinela.sign.document'].with_user(self.user_a).browse(
                self.doc_a.id
            ).write({'signed_by': 'hacker'})

    def test_bac_unlink_denied(self):
        with self.assertRaises(AccessError):
            self.env['sentinela.sign.document'].with_user(self.user_a).browse(
                self.doc_a.id
            ).unlink()

    # ---- Estructural: record rules presentes y con filtro de partner ----
    def test_record_rules_present_and_partner_scoped(self):
        Rule = self.env['ir.rule'].sudo()
        group = self.env.ref('sentinela_api.group_coc_portal')
        for model in EXPOSED_MODELS:
            rules = Rule.search([('model_id.model', '=', model), ('groups', 'in', group.id)])
            self.assertTrue(rules, "Falta record rule COC para %s" % model)
            self.assertTrue(
                any('partner_id' in (r.domain_force or '') for r in rules),
                "La record rule de %s no filtra por partner_id" % model,
            )

    # ---- Estructural: ACL del grupo COC es read-only ----
    def test_acl_is_read_only(self):
        Access = self.env['ir.model.access'].sudo()
        group = self.env.ref('sentinela_api.group_coc_portal')
        for model in ACL_READONLY_MODELS:
            accs = Access.search([('model_id.model', '=', model), ('group_id', '=', group.id)])
            self.assertTrue(accs, "Falta ACL COC para %s" % model)
            for a in accs:
                self.assertFalse(
                    a.perm_write or a.perm_create or a.perm_unlink,
                    "El ACL COC de %s debe ser solo lectura" % model,
                )

    # ---- Regresion del hueco real detectado en STAGING (sign.document) ----
    def test_preexisting_portal_user_is_isolated(self):
        """Un usuario SOLO en base.group_portal (creado por otro flujo, sin grupo COC)
        NO debe ver documentos de otro cliente. Reproduce la fuga detectada en STAGING."""
        pc = self.env['res.partner'].create({'name': 'Cliente C COC'})
        pd = self.env['res.partner'].create({'name': 'Cliente D COC'})
        portal_only = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Portal Solo C',
            'login': 'portalonly.c@portal.test',
            'partner_id': pc.id,
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })
        pdf = base64.b64encode(b'%PDF-1.4 t')
        Doc = self.env['sentinela.sign.document'].sudo()
        doc_c = Doc.create({'partner_id': pc.id, 'file': pdf})
        doc_d = Doc.create({'partner_id': pd.id, 'file': pdf})

        seen = self.env['sentinela.sign.document'].with_user(portal_only).search([])
        self.assertIn(doc_c, seen)
        self.assertNotIn(
            doc_d, seen,
            "FUGA: un usuario solo-portal no debe ver documentos de otro cliente",
        )

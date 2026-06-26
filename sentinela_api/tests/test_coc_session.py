# -*- coding: utf-8 -*-
"""W5.6 — Tests del handshake de sesión Odoo efímera (regresión en CI).

Cubre a nivel de servicio (in-process) las garantías validadas dinámicamente en
STAGING por HTTP: usuario correcto, sin credenciales permanentes, revocación,
expiración, anti-escalada (solo portal), secreto fail-closed, errores y auditoría.
"""
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'sentinela_api', 'security')
class TestCocSession(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.svc = cls.env['sentinela.coc.session.service']
        cls.env['ir.config_parameter'].sudo().set_param(
            'sentinela_api.gateway_shared_secret', 'test-secret-xyz'
        )
        cls.partner = cls.env['res.partner'].create({'name': 'COC Sess A'})

    def _close(self, sid):
        if sid:
            self.svc.close_portal_session(sid)

    def test_secret_fail_closed(self):
        self.assertTrue(self.svc._check_secret('test-secret-xyz'))
        self.assertFalse(self.svc._check_secret('wrong'))
        self.assertFalse(self.svc._check_secret(None))

    def test_open_represents_correct_portal_user(self):
        r = self.svc.open_portal_session(self.partner.id, ttl_seconds=900)
        self.assertTrue(r['ok'])
        sid = r['session_id']
        try:
            user = self.env['res.users'].browse(r['uid'])
            self.assertEqual(user.partner_id, self.partner)   # usuario correcto
            self.assertTrue(user.share)                       # portal (no interno)
            self.assertTrue(self.svc.check_portal_session(sid)['ok'])
        finally:
            self._close(sid)

    def test_revocation_immediate(self):
        r = self.svc.open_portal_session(self.partner.id, ttl_seconds=900)
        sid = r['session_id']
        self.assertTrue(self.svc.close_portal_session(sid)['ok'])
        self.assertEqual(self.svc.check_portal_session(sid).get('error'), 'not_found')

    def test_expiry_auto(self):
        r = self.svc.open_portal_session(self.partner.id, ttl_seconds=0)
        self.assertEqual(self.svc.check_portal_session(r['session_id']).get('error'), 'expired')

    def test_partner_not_found(self):
        self.assertEqual(
            self.svc.open_portal_session(999999999).get('error'), 'partner_not_found'
        )

    def test_disabled_user_rejected(self):
        p = self.env['res.partner'].create({'name': 'COC Sess Dis'})
        u = self.env['res.users']._coc_ensure_portal_user(p)
        u.active = False
        self.assertEqual(self.svc.open_portal_session(p.id).get('error'), 'user_disabled')

    def test_audit_logged(self):
        before = self.env['sentinela.coc.auth.log'].search_count([])
        r = self.svc.open_portal_session(self.partner.id, ttl_seconds=60)
        self._close(r.get('session_id'))
        self.assertGreater(self.env['sentinela.coc.auth.log'].search_count([]), before)

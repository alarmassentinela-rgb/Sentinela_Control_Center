# -*- coding: utf-8 -*-
"""W5.6 — Handshake de identidad: sesión Odoo EFÍMERA del usuario portal.

Garantías del modelo de confianza:
- La sesión representa SIEMPRE al usuario portal correcto (uid del partner verificado).
- NUNCA se usan credenciales permanentes (no API keys): se crea una sesión Odoo
  estándar (uid + session_token ligado al sid) que se puede revocar y expira.
- Revocación inmediata (borrado del session_store) y expiración (TTL + GC lazy).
- Respeta las record rules de WS-2 (la sesión corre como el usuario portal).
- El Gateway NO puede elevar privilegios: solo se abren sesiones de usuarios
  `share` (portal); jamás de usuarios internos.
- Toda operación queda auditada (`sentinela.coc.auth.log` + logger).
- Seguro ante reinicios: la sesión vive en el FilesystemSessionStore (persistente).
"""
import hmac
import logging
import re
from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.http import root

_logger = logging.getLogger('sentinela_api.security')
PARAM_SECRET = 'sentinela_api.gateway_shared_secret'


class CocAuthLog(models.Model):
    _name = 'sentinela.coc.auth.log'
    _description = 'COC — Auditoría de autenticación (server-side)'
    _order = 'create_date desc'

    event_type = fields.Char(index=True)
    partner_id = fields.Many2one('res.partner', index=True, ondelete='set null')
    user_id = fields.Many2one('res.users', index=True, ondelete='set null')
    sid = fields.Char(string='Session (parcial)')
    success = fields.Boolean(default=True)
    ip = fields.Char()
    user_agent = fields.Char()
    detail = fields.Char()


class CocSessionService(models.AbstractModel):
    _name = 'sentinela.coc.session.service'
    _description = 'COC — Servicio de sesiones Odoo efímeras del portal'

    # ---- auditoría ----
    @api.model
    def _audit(self, event_type, success=True, partner=None, user=None, sid=None,
               ip=None, ua=None, detail=None):
        try:
            self.env['sentinela.coc.auth.log'].sudo().create({
                'event_type': event_type,
                'success': success,
                'partner_id': partner.id if partner else False,
                'user_id': user.id if user else False,
                'sid': (sid[:10] + '…') if sid else False,  # nunca el sid completo
                'ip': ip,
                'user_agent': (ua or '')[:400] or False,
                'detail': detail,
            })
        except Exception:
            _logger.exception('COC: fallo al escribir auditoría')
        _logger.info('COC auth event=%s ok=%s partner=%s user=%s ip=%s detail=%s',
                     event_type, success, partner and partner.id, user and user.id, ip, detail)

    # ---- secreto compartido (fail-closed, comparación constante) ----
    @api.model
    def _check_secret(self, provided):
        expected = self.env['ir.config_parameter'].sudo().get_param(PARAM_SECRET)
        if not expected:
            _logger.error('COC: %s no configurado — rechazando (fail closed)', PARAM_SECRET)
            return False
        return bool(provided) and hmac.compare_digest(str(provided), str(expected))

    # ---- resolver teléfono -> partner (el Gateway no decide el partner) ----
    @api.model
    def resolve_phone(self, phone):
        digits = re.sub(r"\D", "", phone or "")
        last10 = digits[-10:]
        if len(last10) < 10:
            return {"ok": False, "error": "bad_phone"}
        Partner = self.env["res.partner"].sudo()
        p = Partner.search(["|", ("phone", "like", last10), ("mobile", "like", last10)], limit=1)
        if not p:
            return {"ok": False, "error": "not_found"}
        return {"ok": True, "partner_id": p.id}

    # ---- abrir sesión efímera ----
    @api.model
    def open_portal_session(self, partner_id, ttl_seconds=900, device=None, ip=None, user_agent=None):
        try:
            pid = int(partner_id)
        except (TypeError, ValueError):
            self._audit('session_open', False, ip=ip, ua=user_agent, detail='partner_id invalido')
            return {'ok': False, 'error': 'bad_request'}

        partner = self.env['res.partner'].sudo().browse(pid).exists()
        if not partner:
            self._audit('session_open', False, ip=ip, ua=user_agent, detail='partner inexistente %s' % pid)
            return {'ok': False, 'error': 'partner_not_found'}

        user = self.env['res.users'].sudo()._coc_ensure_portal_user(partner)
        if not user or not user.active:
            self._audit('session_open', False, partner=partner, user=user, ip=ip, ua=user_agent,
                        detail='usuario deshabilitado')
            return {'ok': False, 'error': 'user_disabled'}
        # No escalar privilegios: solo usuarios portal (share).
        if not user.share:
            self._audit('session_open', False, partner=partner, user=user, ip=ip, ua=user_agent,
                        detail='usuario NO portal (bloqueado por anti-escalada)')
            return {'ok': False, 'error': 'not_portal_user'}

        store = root.session_store
        sess = store.new()
        sess.uid = user.id
        sess.login = user.login
        sess.db = self.env.cr.dbname
        sess.context = {}
        sess.session_token = user._compute_session_token(sess.sid)
        expires = fields.Datetime.now() + timedelta(seconds=max(0, int(ttl_seconds)))
        sess['coc_expires_at'] = fields.Datetime.to_string(expires)
        sess['coc_managed'] = True
        store.save(sess)

        self._audit('session_open', True, partner=partner, user=user, sid=sess.sid, ip=ip, ua=user_agent,
                    detail='ttl=%ss device=%s' % (ttl_seconds, device))
        return {'ok': True, 'session_id': sess.sid, 'uid': user.id,
                'expires_at': sess['coc_expires_at']}

    # ---- validar sesión (con expiración lazy) ----
    @api.model
    def check_portal_session(self, session_id):
        store = root.session_store
        sess = store.get(session_id or '')
        if not sess or not sess.get('uid') or not sess.get('coc_managed'):
            return {'ok': False, 'error': 'not_found'}
        user = self.env['res.users'].sudo().browse(sess['uid'])
        if (not user.exists() or not user.active
                or sess.get('session_token') != user._compute_session_token(sess.sid)):
            return {'ok': False, 'error': 'invalid'}
        exp = sess.get('coc_expires_at')
        if exp and fields.Datetime.from_string(exp) <= fields.Datetime.now():
            store.delete(sess)  # GC lazy: no dejar recursos abiertos
            self._audit('session_expired', True, user=user, sid=session_id, detail='gc lazy')
            return {'ok': False, 'error': 'expired'}
        return {'ok': True, 'uid': sess['uid'], 'expires_at': exp}

    # ---- cerrar sesión (revocación inmediata) ----
    @api.model
    def close_portal_session(self, session_id):
        store = root.session_store
        sess = store.get(session_id or '')
        if sess and sess.get('uid') and sess.get('coc_managed'):
            uid = sess.get('uid')
            store.delete(sess)
            self._audit('session_close', True, sid=session_id, detail='uid=%s' % uid)
            return {'ok': True}
        self._audit('session_close', False, sid=session_id, detail='no encontrada/ajena')
        return {'ok': False, 'error': 'not_found'}

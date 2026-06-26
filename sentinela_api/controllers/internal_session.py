# -*- coding: utf-8 -*-
"""W5.6 — Endpoints INTERNOS del handshake (gateway ↔ Odoo).

Protegidos por SECRETO COMPARTIDO (header X-COC-Secret, fail-closed). Deben quedar
restringidos a la LAN (firewall/NPM): NO exponer a internet. type='json'.
El `partner_id` lo verifica el Gateway (tras OTP); Odoo abre la sesión efímera.
"""
from odoo import http
from odoo.http import request

SECRET_HEADER = 'X-COC-Secret'


class CocInternalSession(http.Controller):

    def _svc(self):
        return request.env['sentinela.coc.session.service'].sudo()

    def _secret(self):
        return request.httprequest.headers.get(SECRET_HEADER)

    def _ip(self):
        return (request.httprequest.headers.get('X-Forwarded-For')
                or request.httprequest.remote_addr)

    def _peer(self):
        # IP real del peer TCP (no spoofeable por header) para la allowlist LAN
        return request.httprequest.remote_addr

    def _ua(self):
        return request.httprequest.headers.get('User-Agent')

    @http.route('/coc/internal/identity/resolve', type='json', auth='public', methods=['POST'], csrf=False)
    def resolve(self, phone=None, **kw):
        svc = self._svc()
        if not svc._check_secret(self._secret()) or not svc._check_origin(self._peer()):
            return {'ok': False, 'error': 'forbidden'}
        return svc.resolve_phone(phone)

    @http.route('/coc/internal/identity/set_phone', type='json', auth='public', methods=['POST'], csrf=False)
    def set_phone(self, partner_id=None, phone=None, **kw):
        svc = self._svc()
        if not svc._check_secret(self._secret()) or not svc._check_origin(self._peer()):
            return {'ok': False, 'error': 'forbidden'}
        return svc.set_partner_phone(partner_id, phone)

    @http.route('/coc/internal/session/open', type='json', auth='public', methods=['POST'], csrf=False)
    def open(self, partner_id=None, ttl_seconds=900, device=None, **kw):
        svc = self._svc()
        if not svc._check_secret(self._secret()) or not svc._check_origin(self._peer()):
            svc._audit('session_open', False, ip=self._ip(), ua=self._ua(), detail='secreto invalido')
            return {'ok': False, 'error': 'forbidden'}
        return svc.open_portal_session(partner_id, ttl_seconds, device, self._ip(), self._ua())

    @http.route('/coc/internal/session/check', type='json', auth='public', methods=['POST'], csrf=False)
    def check(self, session_id=None, **kw):
        svc = self._svc()
        if not svc._check_secret(self._secret()) or not svc._check_origin(self._peer()):
            return {'ok': False, 'error': 'forbidden'}
        return svc.check_portal_session(session_id)

    @http.route('/coc/internal/session/close', type='json', auth='public', methods=['POST'], csrf=False)
    def close(self, session_id=None, **kw):
        svc = self._svc()
        if not svc._check_secret(self._secret()) or not svc._check_origin(self._peer()):
            return {'ok': False, 'error': 'forbidden'}
        return svc.close_portal_session(session_id)

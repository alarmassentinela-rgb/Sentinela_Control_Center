# -*- coding: utf-8 -*-
"""POST /coc/internal/cfdi/stamp — timbra un CFDI (S2-010), async/reintetable.

INTERNO (shared-secret, LAN). Reusa `action_cfdi_stamp_prodigia` de
sentinela_cfdi_prodigia. Idempotente: si ya está timbrada (cfdi_status='valid'),
devuelve `emitted` sin re-timbrar. Si el PAC falla, devuelve `pending_retriable`
SIN lanzar (el pago sigue válido; el CFDI se reintenta). Validación viva: S2-015.
"""
from odoo import http
from odoo.http import request

SECRET_HEADER = 'X-COC-Secret'


class CocInternalCfdi(http.Controller):

    def _guard(self):
        svc = request.env['sentinela.coc.session.service'].sudo()
        secret = request.httprequest.headers.get(SECRET_HEADER)
        return svc._check_secret(secret) and svc._check_origin(request.httprequest.remote_addr)

    @http.route('/coc/internal/cfdi/stamp', type='json', auth='public', methods=['POST'], csrf=False)
    def stamp(self, invoice_id=None, **kw):
        if not self._guard():
            return {'ok': False, 'error': 'forbidden'}
        move = request.env['account.move'].sudo().browse(invoice_id).exists()
        if not move:
            return {'ok': False, 'error': 'not_found'}

        # Idempotencia: ya timbrada -> emitted (sin re-timbrar).
        if move.cfdi_status == 'valid' and move.cfdi_uuid:
            return {'ok': True, 'status': 'emitted', 'uuid': move.cfdi_uuid}

        try:
            move.action_cfdi_stamp_prodigia()
        except Exception as e:   # noqa: BLE001 — fallo del PAC NO invalida el pago
            return {'ok': True, 'status': 'pending_retriable', 'reason': str(e)[:300]}

        move.invalidate_recordset(['cfdi_status', 'cfdi_uuid', 'cfdi_message'])
        if move.cfdi_status == 'valid' and move.cfdi_uuid:
            return {'ok': True, 'status': 'emitted', 'uuid': move.cfdi_uuid}
        return {'ok': True, 'status': 'pending_retriable', 'reason': move.cfdi_message or 'pac_error'}

# -*- coding: utf-8 -*-
"""POST /coc/internal/notify/payment_confirmed (S2-012) — shared-secret, LAN.

REUSA el canal de correo existente de Odoo para confirmar el pago al cliente. NO crea
mensajería nueva. Validación viva / plantilla branded definitiva: S2-015.
"""
from odoo import http
from odoo.http import request

SECRET_HEADER = 'X-COC-Secret'


class CocInternalNotify(http.Controller):

    def _guard(self):
        svc = request.env['sentinela.coc.session.service'].sudo()
        secret = request.httprequest.headers.get(SECRET_HEADER)
        return svc._check_secret(secret) and svc._check_origin(request.httprequest.remote_addr)

    @http.route('/coc/internal/notify/payment_confirmed', type='json', auth='public', methods=['POST'], csrf=False)
    def payment_confirmed(self, partner_id=None, payment_id=None, amount=0.0, currency='MXN', **kw):
        if not self._guard():
            return {'ok': False, 'error': 'forbidden'}
        partner = request.env['res.partner'].sudo().browse(partner_id).exists()
        if not partner:
            return {'ok': False, 'error': 'not_found'}

        # Reusa el canal de mail de Odoo (mismo medio que el resto de la facturación).
        cuerpo = (
            'Hemos recibido tu pago por <b>%s %s</b>. ¡Gracias! '
            'Tu estado de cuenta ya está actualizado.' % (currency, amount)
        )
        partner.message_post(
            body=cuerpo,
            subject='Confirmación de pago',
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        return {'ok': True}

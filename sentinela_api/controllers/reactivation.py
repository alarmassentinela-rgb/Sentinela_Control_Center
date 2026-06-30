# -*- coding: utf-8 -*-
"""Endpoints internos de Reactivación (S2-011) — shared-secret, LAN.

Entregan HECHOS del servicio asociado a una factura y ejecutan la reactivación.
La POLÍTICA (3 condiciones) vive en el gateway; aquí solo hechos + acción, sobre
sentinela_subscriptions (state=='suspension' / action_reactivate).

Vinculación factura↔suscripción y 'vencidas por servicio': se confirman/ajustan en
S2-015 contra Odoo vivo (STAGING Sprint 1 congelado).
"""
from odoo import fields, http
from odoo.http import request

SECRET_HEADER = 'X-COC-Secret'
OUT_TYPES = ['out_invoice', 'out_refund']


class CocInternalReactivation(http.Controller):

    def _guard(self):
        svc = request.env['sentinela.coc.session.service'].sudo()
        secret = request.httprequest.headers.get(SECRET_HEADER)
        return svc._check_secret(secret) and svc._check_origin(request.httprequest.remote_addr)

    def _subscription_for_invoice(self, move):
        """Suscripción (servicio) dueña de la factura. Best-effort: por el M2M
        account.move.subscription_ids (preferencia de facturación) y, si no, por partner."""
        Sub = request.env['sentinela.subscription'].sudo()
        if 'subscription_ids' in move._fields and move.subscription_ids:
            return move.subscription_ids[:1]
        return Sub.search([('partner_id', '=', move.partner_id.id)], limit=1)

    @http.route('/coc/internal/reactivation/service_state', type='json', auth='public', methods=['POST'], csrf=False)
    def service_state(self, invoice_id=None, **kw):
        if not self._guard():
            return {'ok': False, 'error': 'forbidden'}
        move = request.env['account.move'].sudo().browse(invoice_id).exists()
        if not move:
            return {'ok': True, 'service_id': None}
        sub = self._subscription_for_invoice(move)
        if not sub:
            return {'ok': True, 'service_id': None}

        today = fields.Date.context_today(request.env.user)
        # ¿Otras facturas vencidas del servicio? (del partner, distintas a esta, vencidas y no pagadas)
        otras = request.env['account.move'].sudo().search([
            ('move_type', 'in', OUT_TYPES), ('state', '=', 'posted'),
            ('partner_id', '=', sub.partner_id.id), ('id', '!=', move.id),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ])
        has_other_overdue = any(m.invoice_date_due and m.invoice_date_due < today for m in otras)
        return {
            'ok': True,
            'service_id': sub.id,
            'suspended_for_collections': sub.state == 'suspension',
            'has_other_overdue': has_other_overdue,
        }

    @http.route('/coc/internal/reactivation/reactivate', type='json', auth='public', methods=['POST'], csrf=False)
    def reactivate(self, service_id=None, **kw):
        if not self._guard():
            return {'ok': False, 'error': 'forbidden'}
        sub = request.env['sentinela.subscription'].sudo().browse(service_id).exists()
        if not sub:
            return {'ok': False, 'error': 'not_found'}
        if sub.state == 'suspension':
            sub.action_reactivate()
        return {'ok': True, 'service_id': sub.id, 'state': sub.state}

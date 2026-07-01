# -*- coding: utf-8 -*-
"""POST /coc/internal/payments/apply — aplica un pago confirmado (S2-009).

INTERNO (shared-secret, LAN; NO exponer a internet). Crea el pago del cliente y lo
concilia contra sus facturas ABIERTAS; idempotente por `external_ref` (no crea dos
veces el mismo pago). Reporta qué facturas quedaron liquidadas y cuáles ya estaban
pagadas (conciliación anti doble-pago con depósito OXXO/banco).

NO calcula reglas de negocio de Cobranza: solo ejecuta la escritura contable y
reporta hechos. La verificación viva es S2-015 (STAGING Sprint 1 congelado).
"""
from odoo import SUPERUSER_ID, http
from odoo.http import request

SECRET_HEADER = 'X-COC-Secret'
OUT_TYPES = ['out_invoice', 'out_refund']


class CocInternalPayments(http.Controller):

    def _guard(self):
        svc = request.env['sentinela.coc.session.service'].sudo()
        secret = request.httprequest.headers.get(SECRET_HEADER)
        peer = request.httprequest.remote_addr
        return svc._check_secret(secret) and svc._check_origin(peer)

    @http.route('/coc/internal/payments/apply', type='json', auth='public', methods=['POST'], csrf=False)
    def apply(self, partner_id=None, invoice_ids=None, amount=0.0, currency='MXN', external_ref=None, **kw):
        if not self._guard():
            return {'ok': False, 'error': 'forbidden'}
        if not partner_id or not invoice_ids or not external_ref:
            return {'ok': False, 'error': 'bad_request'}

        # UAT-002 (Sprint 2, decisión controlada): account.payment.register.
        # action_create_payments() NO honra el flag su de .sudo() para la escritura de
        # account.move, por lo que el usuario público (uid 4) provoca AccessError. Se
        # ejecuta como SUPERUSER_ID por no existir un usuario técnico con permisos de
        # contabilidad. Sprint 3 (backlog): sustituir por un usuario técnico dedicado.
        env = request.env(user=SUPERUSER_ID)
        Move = env['account.move'].sudo()
        Payment = env['account.payment'].sudo()

        invoices = Move.browse(invoice_ids).exists().filtered(
            lambda m: m.move_type in OUT_TYPES and m.partner_id.id == partner_id and m.state == 'posted')
        already_paid = [m.id for m in invoices if m.payment_state == 'paid']
        abiertas = invoices.filtered(lambda m: m.payment_state in ('not_paid', 'partial'))

        # Idempotencia: ¿ya existe el pago con este external_ref?
        existente = Payment.search([('partner_id', '=', partner_id), ('memo', '=', external_ref)], limit=1)
        if existente:
            ya = [m.id for m in invoices if m.payment_state == 'paid']
            return {'ok': True, 'created': False, 'paid': ya, 'already_paid': already_paid}

        if not abiertas:
            # Nada por liquidar (todo ya conciliado por otro medio): no se crea pago.
            return {'ok': True, 'created': False, 'paid': [], 'already_paid': already_paid}

        # Crear + conciliar con el asistente estándar de Odoo (registra y concilia).
        wizard = env['account.payment.register'].sudo().with_context(
            active_model='account.move', active_ids=abiertas.ids).create({
                'amount': amount,
                'communication': external_ref,
            })
        wizard.payment_difference_handling = 'open'   # no fuerza saldo; concilia lo que cubra
        wizard.action_create_payments()
        # Etiqueta el pago con el external_ref para idempotencia futura.
        nuevo = Payment.search([('partner_id', '=', partner_id), ('memo', 'in', (external_ref, False))],
                               order='id desc', limit=1)
        if nuevo and not nuevo.memo:
            nuevo.memo = external_ref

        abiertas.invalidate_recordset(['payment_state'])
        paid = [m.id for m in abiertas if m.payment_state == 'paid']
        return {'ok': True, 'created': True, 'paid': paid, 'already_paid': already_paid}

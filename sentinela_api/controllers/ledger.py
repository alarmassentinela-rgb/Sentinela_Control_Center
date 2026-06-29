# -*- coding: utf-8 -*-
"""GET /v1/ledger/movements — movimientos contables NORMALIZADOS (SOLO LECTURA).

Fuente de datos del Ledger (capacidad de Cobranza, Sprint 2). auth='user' (act-as):
las record rules acotan los datos a SUS movimientos (misma garantia que billing.py).
Normaliza cargos (facturas), notas (notas de credito) y pagos a un stream uniforme:
{kind, id, date, amount, currency, reference, status, service_id}. NO duplica la
contabilidad: lee del contable existente.

Nota: la atribucion por servicio (service_id) se incorpora en S2-004 (Estado de
Cuenta por servicio); aqui service_id viaja como None.
"""
from odoo import http
from odoo.http import request

from .main import API_PREFIX

OUT_TYPES = ['out_invoice', 'out_refund']


class LedgerController(http.Controller):

    @http.route(API_PREFIX + '/ledger/movements', type='http', auth='user', methods=['GET'], csrf=False)
    def movements(self, **kw):
        from .main import json_ok
        items = []

        # Cargos (facturas) y notas (notas de credito) del cliente. search() como
        # usuario portal -> record rules acotan; lectura de campos via sudo (igual
        # que billing.py: la propiedad ya quedo garantizada por la record rule).
        moves = request.env['account.move'].search(
            [('move_type', 'in', OUT_TYPES), ('state', '=', 'posted')],
            order='invoice_date, id')
        for m in moves:
            ms = m.sudo()
            items.append({
                'kind': 'note' if ms.move_type == 'out_refund' else 'charge',
                'id': ms.id,
                'date': str(ms.invoice_date or ms.date or ''),
                'amount': round(abs(ms.amount_total), 2),
                'currency': ms.currency_id.name or 'MXN',
                'reference': ms.name or '',
                'status': ms.payment_state,
                'service_id': None,
                # Hechos para el Estado de Cuenta (el Ledger los interpreta, no aqui):
                'due_date': str(ms.invoice_date_due or ''),
                'amount_residual': round(ms.amount_residual, 2),
            })

        # Pagos entrantes del cliente.
        pays = request.env['account.payment'].search(
            [('partner_type', '=', 'customer'), ('payment_type', '=', 'inbound')],
            order='date, id')
        for p in pays:
            ps = p.sudo()
            items.append({
                'kind': 'payment',
                'id': ps.id,
                'date': str(ps.date or ''),
                'amount': round(abs(ps.amount), 2),
                'currency': ps.currency_id.name or 'MXN',
                'reference': ps.name or '',
                'status': ps.state,
                'service_id': None,
            })

        return json_ok({'items': items})

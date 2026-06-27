# -*- coding: utf-8 -*-
"""GET /v1/billing/* — Facturacion (SOLO CONSULTA).

auth='user' (usuario portal). El aislamiento lo dan las record rules (WS-2) sobre
account.move y account.payment: `search` solo trae lo del cliente; el detalle por
id se resuelve via `search` (anti-IDOR). PDF/XML: se verifica propiedad con `search`
y luego se renderiza/lee con sudo (el render QWeb y el adjunto del CFDI necesitan
privilegios internos; la propiedad ya quedo garantizada por la record rule).

NO hay escrituras ni acciones de pago: este recurso es de solo lectura.
"""
import base64

from odoo import fields, http
from odoo.http import request

from .main import API_PREFIX, json_ok, problem
from ..lib.serializers import serialize_invoice, serialize_payment

OUT_TYPES = ['out_invoice', 'out_refund']


def _paging(kw):
    try:
        page = max(1, int(kw.get('page', 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        limit = min(100, max(1, int(kw.get('limit', 20))))
    except (TypeError, ValueError):
        limit = 20
    return page, limit, (page - 1) * limit


class BillingController(http.Controller):

    @http.route(API_PREFIX + '/billing/summary', type='http', auth='user', methods=['GET'], csrf=False)
    def summary(self, **kw):
        Move = request.env['account.move']
        open_moves = Move.search([
            ('move_type', 'in', OUT_TYPES),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ])
        today = fields.Date.context_today(request.env.user)
        total_due = sum(open_moves.mapped('amount_residual'))
        overdue = sum(
            m.amount_residual for m in open_moves
            if m.invoice_date_due and m.invoice_date_due < today
        )
        upcoming = open_moves.sorted(lambda m: m.invoice_date_due or m.invoice_date or today)[:5]
        return json_ok({
            'currency': request.env.company.currency_id.name or 'MXN',
            'total_due': round(total_due, 2),
            'overdue_amount': round(overdue, 2),
            'open_count': len(open_moves),
            'upcoming': [serialize_invoice(m.sudo()) for m in upcoming],
        })

    @http.route(API_PREFIX + '/billing/invoices', type='http', auth='user', methods=['GET'], csrf=False)
    def invoices(self, **kw):
        page, limit, offset = _paging(kw)
        Move = request.env['account.move']
        domain = [('move_type', 'in', OUT_TYPES), ('state', '=', 'posted')]
        total = Move.search_count(domain)
        moves = Move.search(domain, order='invoice_date desc, id desc', limit=limit, offset=offset)
        return json_ok({
            'items': [serialize_invoice(m.sudo()) for m in moves],
            'count': total, 'page': page, 'limit': limit,
        })

    @http.route(API_PREFIX + '/billing/invoices/<int:invoice_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def invoice_detail(self, invoice_id, **kw):
        move = request.env['account.move'].search(
            [('id', '=', invoice_id), ('move_type', 'in', OUT_TYPES)], limit=1)
        if not move:
            return problem(404, 'Factura no encontrada')
        return json_ok(serialize_invoice(move.sudo(), detail=True))

    @http.route(API_PREFIX + '/billing/invoices/<int:invoice_id>/pdf', type='http', auth='user', methods=['GET'], csrf=False)
    def invoice_pdf(self, invoice_id, **kw):
        move = request.env['account.move'].search(
            [('id', '=', invoice_id), ('move_type', 'in', OUT_TYPES)], limit=1)
        if not move:
            return problem(404, 'Factura no encontrada')
        pdf, _ = request.env.ref('account.account_invoices').sudo()._render_qweb_pdf(
            'account.account_invoices', [move.id])
        fname = (move.name or 'factura').replace('/', '-')
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="%s.pdf"' % fname),
        ])

    @http.route(API_PREFIX + '/billing/invoices/<int:invoice_id>/xml', type='http', auth='user', methods=['GET'], csrf=False)
    def invoice_xml(self, invoice_id, **kw):
        move = request.env['account.move'].search(
            [('id', '=', invoice_id), ('move_type', 'in', OUT_TYPES)], limit=1)
        if not move:
            return problem(404, 'Factura no encontrada')
        xml_b64 = move.sudo().cfdi_xml
        if not xml_b64:
            return problem(404, 'Esta factura no tiene XML (CFDI) disponible')
        fname = move.sudo().cfdi_xml_filename or ((move.name or 'cfdi').replace('/', '-') + '.xml')
        return request.make_response(base64.b64decode(xml_b64), headers=[
            ('Content-Type', 'application/xml'),
            ('Content-Disposition', 'attachment; filename="%s"' % fname),
        ])

    @http.route(API_PREFIX + '/billing/payments', type='http', auth='user', methods=['GET'], csrf=False)
    def payments(self, **kw):
        page, limit, offset = _paging(kw)
        Pay = request.env['account.payment']
        domain = [('partner_type', '=', 'customer'), ('payment_type', '=', 'inbound')]
        total = Pay.search_count(domain)
        pays = Pay.search(domain, order='date desc, id desc', limit=limit, offset=offset)
        return json_ok({
            'items': [serialize_payment(p.sudo()) for p in pays],
            'count': total, 'page': page, 'limit': limit,
        })

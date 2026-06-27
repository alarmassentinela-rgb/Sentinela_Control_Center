# -*- coding: utf-8 -*-
"""Serializadores (DTO) estables del COC.

Regla: el contrato de la API NO debe romperse si cambia un modelo de Odoo.
Por eso serializamos explicitamente (no exponemos `read()` crudo). Un campo nuevo
en Odoo no aparece en la API hasta que se agrega aqui a proposito.
"""


def serialize_partner(partner):
    """Perfil minimo del cliente para GET /v1/me."""
    return {
        'id': partner.id,
        'name': partner.name,
        'email': partner.email or None,
        'phone': partner.phone or partner.mobile or None,
        'is_company': partner.is_company,
        # Pista de alcance para el empresarial (techo = entidad comercial):
        'commercial_partner_id': partner.commercial_partner_id.id,
    }


# ============================================================
# Sprint 1 — Mis Servicios + Facturacion (solo lectura).
# DTOs independientes de los modelos internos de Odoo: un cambio de campo
# en Odoo NO altera el contrato a menos que se edite aqui a proposito.
# ============================================================

_SUB_INTERVAL = {'1': 'Mensual', '2': 'Bimestral', '3': 'Trimestral', '6': 'Semestral', '12': 'Anual'}
_SUB_SERVICE = {'internet': 'Internet', 'alarm': 'Alarma', 'gps': 'GPS', 'maintenance': 'Mantenimiento', 'domain': 'Dominio'}


def _fmt_address(p):
    if not p:
        return None
    parts = [p.street, p.street2, p.city]
    out = ', '.join([x for x in parts if x])
    return out or None


def _sub_status(sub):
    """Estatus simple y estable, derivado de state + technical_state."""
    if sub.state in ('closed', 'cancelled'):
        return 'inactive'
    if sub.state == 'pending_signature':
        return 'pending_signature'
    if sub.state == 'suspension' or sub.technical_state in ('suspended', 'cut'):
        return 'suspended'
    if sub.state == 'active' and sub.technical_state == 'active':
        return 'active'
    return sub.state


def serialize_subscription(sub):
    """DTO de una suscripcion para Mis Servicios."""
    interval = sub.recurring_interval
    return {
        'id': sub.id,
        'reference': sub.name,
        'service_type': sub.service_type,
        'service_type_label': _SUB_SERVICE.get(sub.service_type, sub.service_type),
        'plan': sub.product_id.display_name or None,
        'status': _sub_status(sub),
        'state': sub.state,
        'technical_state': sub.technical_state,
        'monthly_total': round(sub.price_total or 0.0, 2),
        'currency': 'MXN',
        'billing_interval': interval,
        'billing_interval_label': _SUB_INTERVAL.get(interval, interval),
        'next_billing_date': sub.next_billing_date.isoformat() if sub.next_billing_date else None,
        'service_address': _fmt_address(sub.service_address_id or sub.partner_id),
    }


def serialize_invoice(move, detail=False):
    """DTO de una factura/remision. doc_type se deriva de la presencia de cfdi_uuid."""
    is_factura = bool(move.cfdi_uuid)
    data = {
        'id': move.id,
        'number': move.name or None,
        'date': move.invoice_date.isoformat() if move.invoice_date else None,
        'due_date': move.invoice_date_due.isoformat() if move.invoice_date_due else None,
        'amount_total': round(move.amount_total or 0.0, 2),
        'amount_due': round(move.amount_residual or 0.0, 2),
        'currency': move.currency_id.name or 'MXN',
        'payment_state': move.payment_state,
        'doc_type': 'factura' if is_factura else 'remision',
        'cfdi_status': move.cfdi_status,
        'cfdi_uuid': move.cfdi_uuid or None,
        'has_pdf': True,
        'has_xml': bool(move.cfdi_xml),
    }
    if detail:
        data['cfdi_timestamp'] = move.l10n_mx_edi_cfdi_timestamp or None
        data['lines'] = [
            {
                'name': line.name,
                'quantity': line.quantity,
                'price_subtotal': round(line.price_subtotal or 0.0, 2),
            }
            for line in move.invoice_line_ids if line.display_type in ('product', False)
        ]
    return data


def serialize_payment(payment):
    """DTO de un pago recibido del cliente."""
    return {
        'id': payment.id,
        'date': payment.date.isoformat() if payment.date else None,
        'amount': round(payment.amount or 0.0, 2),
        'currency': payment.currency_id.name or 'MXN',
        'reference': payment.name or payment.ref or None,
    }

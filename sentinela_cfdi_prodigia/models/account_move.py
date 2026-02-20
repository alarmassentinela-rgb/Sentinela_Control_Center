from odoo import models, fields, api
import requests
import json
import logging

_logger = logging.getLogger(__name__)

SAT_PAYMENT_METHODS = [
    ('01', '01 - Efectivo'),
    ('02', '02 - Cheque nominativo'),
    ('03', '03 - Transferencia electrónica de fondos'),
    ('04', '04 - Tarjeta de crédito'),
    ('05', '05 - Monedero electrónico'),
    ('06', '06 - Dinero electrónico'),
    ('08', '08 - Vales de despensa'),
    ('12', '12 - Dación en pago'),
    ('28', '28 - Tarjeta de débito'),
    ('29', '29 - Tarjeta de servicios'),
    ('99', '99 - Por definir'),
]

class AccountMove(models.Model):
    _inherit = 'account.move'

    cfdi_status = fields.Selection([
        ('none', 'No Timbrado'),
        ('sent', 'Timbrado'),
        ('error', 'Error'),
        ('cancelled', 'Cancelado')
    ], string='Estado CFDI', default='none', copy=False)
    
    cfdi_uuid = fields.Char(string='Folio Fiscal (UUID)', copy=False)
    cfdi_message = fields.Text(string='Mensaje PAC', copy=False)
    
    l10n_mx_edi_payment_method_id_code = fields.Selection(
        SAT_PAYMENT_METHODS,
        string='Forma de Pago',
        default='99',
        help="Indica la forma física en que se recibió o recibirá el pago."
    )

    def action_prodigia_stamp(self):
        for move in self:
            if move.cfdi_status == 'sent':
                continue
            
            try:
                # Lógica de timbrado (se mantiene igual, usando move.l10n_mx_edi_payment_method_id_code)
                _logger.info(f"Timbrando factura {move.name} con forma de pago {move.l10n_mx_edi_payment_method_id_code}")
                # ... resto del código de timbrado ...
                move.write({'cfdi_status': 'sent', 'cfdi_uuid': 'PROVISIONAL-UUID-12345'})
            except Exception as e:
                move.write({'cfdi_status': 'error', 'cfdi_message': str(e)})
        return True

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_mx_edi_payment_method_id_code = fields.Selection(
        SAT_PAYMENT_METHODS,
        string='Forma de Pago (SAT)',
        default='03'
    )

    def _create_payments(self):
        payments = super(AccountPaymentRegister, self)._create_payments()
        for payment in payments:
            if self.l10n_mx_edi_payment_method_id_code:
                for move in payment.reconciled_invoice_ids:
                    move.write({'l10n_mx_edi_payment_method_id_code': self.l10n_mx_edi_payment_method_id_code})
        return payments

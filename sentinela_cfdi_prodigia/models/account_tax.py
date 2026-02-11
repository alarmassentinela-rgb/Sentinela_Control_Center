from odoo import models, fields

class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_mx_edi_tax_code = fields.Selection([
        ('001', '001 - ISR'),
        ('002', '002 - IVA'),
        ('003', '003 - IEPS'),
    ], string='Clave Impuesto SAT', default='002')

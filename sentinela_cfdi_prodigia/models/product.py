from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_mx_edi_code_sat = fields.Char(string='Clave SAT', help='Ej. 81111503')
    l10n_mx_edi_um_code_sat = fields.Char(string='Clave Unidad SAT', default='E48', help='Ej. E48 para Servicio')

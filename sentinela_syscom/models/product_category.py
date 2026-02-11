from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    syscom_category_id = fields.Char(string='Syscom Category ID', help="ID de la categoría en Syscom")

from odoo import models, fields, api

class FSMEquipment(models.Model):
    _name = 'sentinela.fsm.equipment'
    _description = 'Equipo/Material para Órdenes de Servicio'

    order_id = fields.Many2one('sentinela.fsm.order', string='Orden de Servicio', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    quantity = fields.Float(string='Cantidad', default=1.0, required=True)
    unit_price = fields.Float(string='Precio Unitario')
    total_price = fields.Float(string='Precio Total', compute='_compute_total_price', store=True)
    notes = fields.Char(string='Notas')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_price = self.product_id.standard_price

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.quantity * record.unit_price
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SubscriptionSelectionWizard(models.TransientModel):
    _name = 'sentinela.subscription.selection.wizard'
    _description = 'Selector de Equipo desde Venta'

    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción')
    sale_order_id = fields.Many2one('sale.order', string='Cotización')
    line_ids = fields.Many2many('sale.order.line', string='Equipos Disponibles')
    selected_line_id = fields.Many2one('sale.order.line', string='Equipo a Vincular', 
                                       domain="[('id', 'in', line_ids)]")

    def action_confirm(self):
        self.ensure_one()
        if not self.selected_line_id:
            raise UserError("Debe seleccionar un equipo de la lista.")
        
        line = self.selected_line_id
        product = line.product_id
        
        vals = {
            'equipment_brand': product.brand_id.name if hasattr(product, 'brand_id') else 'Genérico',
            'equipment_model': product.name,
            'serial_number_id': line.lot_id.id if hasattr(line, 'lot_id') and line.lot_id else False,
            'equipment_serial': line.lot_id.name if hasattr(line, 'lot_id') and line.lot_id else product.default_code
        }
        
        # Si es GPS, intentar poner el IMEI
        if self.subscription_id.service_type == 'gps' and vals.get('equipment_serial'):
            vals['gps_imei'] = vals['equipment_serial']

        self.subscription_id.write(vals)
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Equipo vinculado correctamente',
                'type': 'rainbow_man',
            }
        }

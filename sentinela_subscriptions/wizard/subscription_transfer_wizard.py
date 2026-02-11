from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SentinelaSubscriptionTransfer(models.TransientModel):
    _name = 'sentinela.subscription.transfer'
    _description = 'Asistente para Cambio de Domicilio'

    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción', required=True)
    partner_id = fields.Many2one(related='subscription_id.partner_id', string='Cliente')
    current_address_id = fields.Many2one(related='subscription_id.service_address_id', string='Dirección Actual')
    
    # Mode Selection
    mode = fields.Selection([
        ('existing', 'Seleccionar Existente'),
        ('new', 'Crear Nueva Dirección')
    ], string='Modo', default='existing', required=True)

    # Existing
    new_address_id = fields.Many2one('res.partner', string='Nueva Dirección', 
                                     domain="[('parent_id', '=', partner_id), ('id', '!=', current_address_id)]")
    
    # New
    street = fields.Char(string='Calle y Número')
    street2 = fields.Char(string='Colonia / Interior')
    city = fields.Char(string='Ciudad')
    zip_code = fields.Char(string='Código Postal')
    state_id = fields.Many2one('res.country.state', string='Estado')
    
    transfer_price = fields.Float(string='Costo del Trámite', required=True, default=350.00)

    @api.model
    def default_get(self, fields):
        res = super(SentinelaSubscriptionTransfer, self).default_get(fields)
        product = self.env.ref('sentinela_subscriptions.product_service_transfer', raise_if_not_found=False)
        if product and 'transfer_price' in fields:
            res['transfer_price'] = product.list_price
        return res

    def action_create_transfer_quote(self):
        self.ensure_one()
        SaleOrder = self.env['sale.order']
        Partner = self.env['res.partner']
        product = self.env.ref('sentinela_subscriptions.product_service_transfer')
        
        target_partner = False
        
        # Logic to determine target address
        if self.mode == 'existing':
            if not self.new_address_id:
                raise UserError("Por favor seleccione una dirección existente.")
            target_partner = self.new_address_id
        else:
            if not self.street:
                raise UserError("Por favor ingrese al menos la calle.")
            
            # Create new address
            target_partner = Partner.create({
                'parent_id': self.partner_id.id,
                'type': 'delivery',
                'name': f"{self.street} (Sucursal)",
                'street': self.street,
                'street2': self.street2,
                'city': self.city,
                'zip': self.zip_code,
                'state_id': self.state_id.id,
                'country_id': self.env.ref('base.mx').id if self.env.ref('base.mx', False) else False
            })

        # Create Quote
        so_vals = {
            'partner_id': self.partner_id.id,
            'subscription_id': self.subscription_id.id,
            'origin': f"Cambio de Domicilio: {self.subscription_id.name}",
            'require_signature': False,
            'require_payment': True,
            'target_transfer_address_id': target_partner.id,
            'note': f"SOLICITUD DE CAMBIO DE DOMICILIO\nNueva Dirección: {target_partner.contact_address}",
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': f"Cambio de Domicilio a: {target_partner.street or ''}, {target_partner.city or ''}",
                'product_uom_qty': 1,
                'price_unit': self.transfer_price,
            })]
        }
        
        so = SaleOrder.create(so_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cotización Cambio de Domicilio',
            'res_model': 'sale.order',
            'res_id': so.id,
            'view_mode': 'form',
            'target': 'current',
        }
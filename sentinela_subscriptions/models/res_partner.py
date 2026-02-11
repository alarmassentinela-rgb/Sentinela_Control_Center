from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_grouping_method = fields.Selection([
        ('individual', 'Una Factura por Servicio (Detallado)'),
        ('by_branch', 'Agrupar por Sucursal'),
        ('global', 'Una Factura Global (Todo junto)')
    ], string='Preferencia de Facturación', default='individual', 
    help="Define cómo prefiere el cliente recibir sus facturas de suscripción.")

    subscription_count = fields.Integer(compute='_compute_subscription_count', string='# Subscriptions')
    
    def _compute_subscription_count(self):
        for partner in self:
            partner.subscription_count = self.env['sentinela.subscription'].search_count([('partner_id', '=', partner.id)])

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subscriptions',
            'view_mode': 'list,form',
            'res_model': 'sentinela.subscription',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    @api.depends('name', 'parent_id.name')
    def _compute_display_name(self):
        if self._context.get('show_only_name'):
            for partner in self:
                partner.display_name = partner.name
        else:
            super()._compute_display_name()

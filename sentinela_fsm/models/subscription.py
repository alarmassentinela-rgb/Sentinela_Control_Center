from odoo import models, fields, api

class SentinelaSubscription(models.Model):
    _inherit = 'sentinela.subscription'

    fsm_order_ids = fields.One2many('sentinela.fsm.order', 'subscription_id', string='Órdenes de Servicio')
    fsm_order_count = fields.Integer(compute='_compute_fsm_order_count', string='# Tickets')
    
    @api.depends('fsm_order_ids')
    def _compute_fsm_order_count(self):
        for sub in self:
            sub.fsm_order_count = len(sub.fsm_order_ids)

    def action_view_fsm_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tickets de Servicio',
            'res_model': 'sentinela.fsm.order',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id, 'default_partner_id': self.partner_id.id}
        }

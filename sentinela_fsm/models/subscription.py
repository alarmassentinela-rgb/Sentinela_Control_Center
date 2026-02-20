from odoo import models, fields, api

class SentinelaSubscription(models.Model):
    _inherit = 'sentinela.subscription'

    fsm_order_ids = fields.One2many('sentinela.fsm.order', 'subscription_id', string='Órdenes de Servicio')
    fsm_order_count = fields.Integer(compute='_compute_fsm_order_count', string='# Tickets')
    
    all_fsm_evidence_ids = fields.Many2many('sentinela.fsm.evidence', string='Expediente de Evidencias', compute='_compute_all_fsm_evidence')

    @api.depends('fsm_order_ids.evidence_ids')
    def _compute_all_fsm_evidence(self):
        for sub in self:
            sub.all_fsm_evidence_ids = sub.fsm_order_ids.mapped('evidence_ids')

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

    @api.model
    def _cron_generate_preventive_maintenance(self):
        """ 
        Busca contratos que requieran mantenimiento preventivo 
        y crea las órdenes de servicio automáticamente.
        """
        today = fields.Date.today()
        # Buscar contratos cuya fecha de mantenimiento sea hoy o haya pasado
        subs_to_service = self.search([
            ('state', '=', 'active'),
            ('maintenance_frequency', '!=', '0'),
            ('next_maintenance_date', '<=', today)
        ])
        
        FsmOrder = self.env['sentinela.fsm.order']
        orders_created = 0
        
        for sub in subs_to_service:
            # Evitar duplicar si ya hay una orden de mantenimiento abierta (Nuevo, Asignado o En Proceso)
            existing_order = FsmOrder.search([
                ('subscription_id', '=', sub.id),
                ('service_type', '=', 'repair'),
                ('stage', 'in', ['new', 'assigned', 'in_progress'])
            ], limit=1)
            
            if not existing_order:
                FsmOrder.create({
                    'partner_id': sub.partner_id.id,
                    'service_address_id': sub.service_address_id.id or sub.partner_id.id,
                    'subscription_id': sub.id,
                    'service_type': 'repair',
                    'priority': '0', # Normal
                    'description': f"MANTENIMIENTO PREVENTIVO PROGRAMADO: Basado en frecuencia {sub.maintenance_frequency} meses.<br/>Último servicio: {sub.last_maintenance_date or 'NUNCA'}",
                })
                orders_created += 1
                sub.message_post(body="AUTOMATIZACIÓN: Se ha generado una orden de mantenimiento preventivo automáticamente.")
        
        return orders_created

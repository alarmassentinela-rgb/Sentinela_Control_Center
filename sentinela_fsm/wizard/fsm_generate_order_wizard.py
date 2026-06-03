from odoo import models, fields, api, _

# Mismas opciones que puede generar una venta (sin 'patrol').
from ..models.product_template import FSM_SALE_SERVICE_TYPES


class FsmGenerateOrderWizard(models.TransientModel):
    _name = 'sentinela.fsm.generate.order.wizard'
    _description = 'Asistente: Generar Orden de Servicio desde Venta'

    sale_order_id = fields.Many2one('sale.order', string='Venta de Origen')
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    service_address_id = fields.Many2one('res.partner', string='Dirección de Servicio',
        domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]")
    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción Relacionada',
        domain="[('partner_id', '=', partner_id)]")

    service_type = fields.Selection(FSM_SALE_SERVICE_TYPES, string='Tipo de Servicio',
        required=True, default='install')
    technician_id = fields.Many2one('res.users', string='Técnico Asignado')
    scheduled_date = fields.Datetime(string='Fecha Programada')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Alta'),
        ('2', 'Urgente'),
        ('3', 'Crítica'),
    ], string='Prioridad', default='0')
    description = fields.Html(string='Descripción del Trabajo', required=True)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and not self.service_address_id:
            self.service_address_id = self.partner_id

    def action_create_order(self):
        self.ensure_one()
        vals = {
            'partner_id': self.partner_id.id,
            'service_address_id': self.service_address_id.id or self.partner_id.id,
            'subscription_id': self.subscription_id.id or False,
            'sale_order_id': self.sale_order_id.id or False,
            'service_type': self.service_type,
            'technician_id': self.technician_id.id or False,
            'scheduled_date': self.scheduled_date or False,
            'priority': self.priority,
            'description': self.description,
        }
        order = self.env['sentinela.fsm.order'].create(vals)

        # Si se asignó técnico de una vez, dejarla en etapa 'assigned' y notificar.
        if self.technician_id:
            order.action_assign()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Orden de Servicio'),
            'res_model': 'sentinela.fsm.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

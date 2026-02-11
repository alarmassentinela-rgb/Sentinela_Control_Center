# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class FSMCreateRouteWizard(models.TransientModel):
    _name = 'sentinela.fsm.create.route.wizard'
    _description = 'Asistente para Crear Ruta FSM'

    technician_id = fields.Many2one('res.users', string='Técnico', required=True)
    date = fields.Date(string='Fecha', required=True, default=fields.Date.today)
    order_ids = fields.Many2many('sentinela.fsm.order', string='Órdenes para la Ruta')
    
    @api.model
    def default_get(self, fields):
        res = super(FSMCreateRouteWizard, self).default_get(fields)
        
        # Obtener órdenes pendientes para el técnico seleccionado
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        
        if active_model == 'res.users' and active_id:
            res['technician_id'] = active_id
            pending_orders = self.env['sentinela.fsm.order'].search([
                ('technician_id', '=', active_id),
                ('stage', 'in', ['assigned', 'new']),
                ('scheduled_date', '=', self.date)
            ])
            res['order_ids'] = [(6, 0, pending_orders.ids)]
        
        return res

    def action_create_route(self):
        """Crear la ruta optimizada"""
        self.ensure_one()
        
        if not self.order_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'Debe seleccionar al menos una orden para crear la ruta.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Crear la ruta optimizada
        route_model = self.env['sentinela.fsm.route.optimization']
        route = route_model.create_route_for_technician(
            self.technician_id,
            self.date,
            self.order_ids.ids
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ruta Optimizada',
            'res_model': 'sentinela.fsm.route.optimization',
            'res_id': route.id,
            'view_mode': 'form',
            'target': 'current',
        }
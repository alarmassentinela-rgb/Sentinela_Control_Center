from odoo import models, fields, api

class FsmTaskTemplate(models.Model):
    _name = 'sentinela.fsm.task.template'
    _description = 'Plantilla de Tarea FSM'

    name = fields.Char(string='Descripción de la Tarea', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    service_type = fields.Selection([
        ('all', 'Todos'),
        ('install', 'Instalación'),
        ('repair', 'Reparación'),
        ('transfer', 'Traslado')
    ], string='Aplica en', default='all')

class FsmOrderLine(models.Model):
    _name = 'sentinela.fsm.order.line'
    _description = 'Línea de Checklist FSM'

    order_id = fields.Many2one('sentinela.fsm.order', string='Orden de Servicio', ondelete='cascade')
    name = fields.Char(string='Tarea', required=True)
    is_done = fields.Boolean(string='Completado')
    notes = fields.Char(string='Observaciones')

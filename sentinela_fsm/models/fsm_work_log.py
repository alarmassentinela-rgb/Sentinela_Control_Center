from odoo import models, fields, api

class SentinelaFsmWorkLog(models.Model):
    _name = 'sentinela.fsm.work.log'
    _description = 'Bitácora de Trabajo FSM'
    _order = 'date desc'

    order_id = fields.Many2one('sentinela.fsm.order', string='Orden de Servicio', ondelete='cascade', required=True)
    technician_id = fields.Many2one('res.users', string='Técnico', default=lambda self: self.env.user)
    date = fields.Datetime(string='Fecha', default=fields.Datetime.now)
    notes = fields.Text(string='Notas / Actividad')
    
    stage_at_moment = fields.Selection([
        ('new', 'Nueva'),
        ('assigned', 'Asignada'),
        ('in_progress', 'En Proceso'),
        ('paused', 'Pausada'),
        ('done', 'Finalizada'),
        ('cancel', 'Cancelada')
    ], string='Estado al Registrar')

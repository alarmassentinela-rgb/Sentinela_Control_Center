from odoo import models, fields

class FSMOrder(models.Model):
    _inherit = 'sentinela.fsm.order'

    alarm_event_id = fields.Many2one('sentinela.alarm.event', string='Evento de Alarma Origen')

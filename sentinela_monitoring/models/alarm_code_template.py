from odoo import models, fields, api

class AlarmCodeTemplate(models.Model):
    _name = 'sentinela.alarm.code.template'
    _description = 'Plantilla Maestra de Códigos de Alarma'

    name = fields.Char(string='Nombre de la Plantilla', required=True, help="Ej. Plantilla Residencial Estándar")
    description = fields.Text(string='Descripción')
    
    line_ids = fields.One2many('sentinela.alarm.code.template.line', 'template_id', string='Configuración de Códigos')
    active = fields.Boolean(default=True)

class AlarmCodeTemplateLine(models.Model):
    _name = 'sentinela.alarm.code.template.line'
    _description = 'Línea de Plantilla de Código'

    template_id = fields.Many2one('sentinela.alarm.code.template', string='Plantilla', ondelete='cascade')
    alarm_code_id = fields.Many2one('sentinela.alarm.code', string='Código de Alarma', required=True)
    
    priority_id = fields.Many2one('sentinela.alarm.priority', string='Prioridad')
    notify_email = fields.Boolean(string='Notificar Email', default=False)
    notify_telegram = fields.Boolean(string='Notificar Telegram', default=False)
    
    notes = fields.Char(string='Notas de Reacción')

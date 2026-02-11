from odoo import models, fields, api

class DeviceAlarmConfig(models.Model):
    _name = 'sentinela.device.alarm.config'
    _description = 'Configuracion de Alarma por Dispositivo'

    device_id = fields.Many2one('sentinela.monitoring.device', string='Dispositivo', ondelete='cascade', required=True)
    alarm_code_id = fields.Many2one('sentinela.alarm.code', string='Código de Alarma', required=True)
    
    # Sobrescribe la prioridad global
    priority_id = fields.Many2one('sentinela.alarm.priority', string='Prioridad Personalizada')
    
    # Notificaciones
    notify_email = fields.Boolean(string='Notificar Email', default=False)
    notify_telegram = fields.Boolean(string='Notificar Telegram', default=False)
    
    _sql_constraints = [
        ('device_code_uniq', 'unique(device_id, alarm_code_id)', 'Ya existe una configuración para este código en este dispositivo.')
    ]

    @api.onchange('alarm_code_id')
    def _onchange_alarm_code_id(self):
        if self.alarm_code_id:
            # Intentar usar priority_id si existe, si no, ignorar (evita crash en migracion)
            if hasattr(self.alarm_code_id, 'priority_id'):
                self.priority_id = self.alarm_code_id.priority_id

from odoo import models, fields, api

class MonitoringZone(models.Model):
    _name = 'sentinela.monitoring.zone'
    _description = 'Zona de Monitoreo'
    _order = 'zone_number asc'

    device_id = fields.Many2one('sentinela.monitoring.device', string='Dispositivo / Panel', required=True, ondelete='cascade')
    zone_number = fields.Integer(string='Número de Zona', required=True, help="El número que envía el panel (Ej. 1, 2, 99)")
    partition = fields.Integer(string='Partición', default=1, help="Área o partición del sistema (Ej. 1=Casa, 2=Garage)")
    
    name = fields.Char(string='Descripción / Ubicación', required=True, help="Ej. Sensor Puerta Principal")
    
    zone_type = fields.Selection([
        ('entry_exit', 'Entrada / Salida'),
        ('perimeter', 'Perimetral (Instantáneo)'),
        ('interior', 'Interior (Seguidor)'),
        ('fire', 'Fuego 24h'),
        ('panic', 'Pánico 24h'),
        ('tamper', 'Sabotaje'),
        ('medical', 'Médico'),
        ('gas', 'Gas / CO'),
        ('water', 'Inundación')
    ], string='Tipo de Zona', required=True)

    is_bypassed = fields.Boolean(string='Anulada (Bypass)', default=False, help="Si la zona está temporalmente desactivada.")
    last_event_date = fields.Datetime(string='Último Evento', readonly=True)

    _sql_constraints = [
        ('zone_device_uniq', 'unique(device_id, zone_number, partition)', 'El número de zona debe ser único por partición en este dispositivo.')
    ]

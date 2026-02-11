from odoo import models, fields, api

class MonitoringDevice(models.Model):
    _name = 'sentinela.monitoring.device'
    _description = 'Dispositivo de Monitoreo'
    _rec_name = 'device_id'

    device_id = fields.Char(string='ID Interno', required=True, default='New')
    account_number = fields.Char(string='Número de Cuenta (Panel)', required=True, help="El código HEX de 4-6 dígitos que envía el panel (Ej. 1234, B52F)")
    
    name = fields.Char(string='Nombre del Dispositivo', compute='_compute_name', store=True)
    
    protocol = fields.Selection([
        ('contact_id', 'Contact ID'),
        ('sia', 'SIA'),
        ('4_2', '4+2'),
        ('ip', 'IP / API Proprietaria')
    ], string='Protocolo de Comunicación', default='contact_id', required=True)

    device_type = fields.Selection([
        ('control_panel', 'Panel de Control'),
        ('sensor_motion', 'Sensor de Movimiento'),
        ('sensor_door', 'Sensor de Puerta'),
        ('sensor_fire', 'Sensor de Fuego'),
        ('panic_button', 'Botón de Pánico'),
        ('camera', 'Cámara'),
        ('siren', 'Sirena'),
        ('other', 'Otro')
    ], string='Tipo de Dispositivo', required=True)
    
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción')
    
    location = fields.Char(string='Ubicación')
    latitude = fields.Float(string='Latitud', digits=(10, 7))
    longitude = fields.Float(string='Longitud', digits=(10, 7))
    
    status = fields.Selection([
        ('active', 'Activo'),
        ('inactive', 'Inactivo'),
        ('maintenance', 'En Mantenimiento'),
        ('faulty', 'Con Fallas'),
        ('offline', 'Desconectado')
    ], string='Estado', default='active', required=True)
    
    last_communication = fields.Datetime(string='Última Comunicación')
    battery_level = fields.Float(string='Nivel de Batería (%)')
    signal_strength = fields.Integer(string='Potencia de Señal (dBm)')
    
    installation_date = fields.Date(string='Fecha de Instalación')
    warranty_expiration = fields.Date(string='Vencimiento de Garantía')
    
    notes = fields.Text(string='Notas')
    
    # Relaciones con eventos y señales
    alarm_event_ids = fields.One2many('sentinela.alarm.event', 'device_id', string='Eventos de Alarma')
    alarm_signal_ids = fields.One2many('sentinela.alarm.signal', 'device_id', string='Señales de Alarma')
    zone_ids = fields.One2many('sentinela.monitoring.zone', 'device_id', string='Zonas Configuradas')
    
    # NUEVO: Configuracion personalizada de codigos por cuenta
    alarm_config_ids = fields.One2many('sentinela.device.alarm.config', 'device_id', string='Configuración de Eventos')

    _sql_constraints = [
        ('account_number_uniq', 'unique(account_number)', 'El número de cuenta del panel debe ser único.')
    ]
    
    @api.depends('device_id', 'partner_id.name')
    def _compute_name(self):
        for device in self:
            if device.partner_id.name:
                device.name = f"{device.device_id} - {device.partner_id.name}"
            else:
                device.name = device.device_id

    def action_activate_device(self):
        """Activar dispositivo"""
        self.write({'status': 'active'})

    def action_deactivate_device(self):
        """Desactivar dispositivo"""
        self.write({'status': 'inactive'})

    def action_set_maintenance(self):
        """Poner en mantenimiento"""
        self.write({'status': 'maintenance'})

    def get_location_map_url(self):
        """Obtener URL para ver ubicación en mapa"""
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
        return None
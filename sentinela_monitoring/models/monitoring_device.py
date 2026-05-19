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
    
    # INTEGRACIÓN CON INVENTARIO (IMEI)
    lot_id = fields.Many2one('stock.lot', string='Número de Serie / IMEI', 
                            help="Seleccione el IMEI desde el inventario físico.")
    
    subscription_id = fields.Many2one(
        'sentinela.subscription', 
        string='Suscripción',
        domain="[('partner_id', '=', partner_id)]",
        help="Vincule este dispositivo con el contrato de servicio correspondiente."
    )

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        """Si se selecciona un IMEI del inventario, usarlo como número de cuenta"""
        if self.lot_id:
            self.account_number = self.lot_id.name
            if not self.location and self.lot_id.product_id:
                self.notes = f"Equipo: {self.lot_id.product_id.display_name}"

    @api.onchange('partner_id')
    def _onchange_partner_id_filter(self):
        """Refuerza el filtro de suscripciones al cambiar el cliente"""
        if self.partner_id:
            # Si hay un cliente, solo mostrar sus suscripciones
            return {'domain': {'subscription_id': [('partner_id', '=', self.partner_id.id)]}}
        else:
            # Si no hay cliente, no mostrar ninguna suscripción
            self.subscription_id = False
            return {'domain': {'subscription_id': [('id', '=', 0)]}}
    
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
    expected_heartbeat_hours = fields.Float(string='Heartbeat Esperado (horas)', default=0.0,
        help="Cada cuántas horas debe reportar el panel. 0 = no monitorear offline. "
             "Si last_communication queda atrasada más de este intervalo, el cron horario "
             "genera un evento trouble 'Panel sin reportar'.")
    battery_level = fields.Float(string='Nivel de Batería (%)')
    signal_strength = fields.Integer(string='Potencia de Señal (dBm)')
    
    installation_date = fields.Date(string='Fecha de Instalación')
    warranty_expiration = fields.Date(string='Vencimiento de Garantía')
    
    notes = fields.Text(string='Notas')
    
    # Relaciones con eventos y señales
    alarm_event_ids = fields.One2many('sentinela.alarm.event', 'device_id', string='Eventos de Alarma')
    alarm_signal_ids = fields.One2many('sentinela.alarm.signal', 'device_id', string='Señales de Alarma')
    zone_ids = fields.One2many('sentinela.monitoring.zone', 'device_id', string='Zonas Configuradas')
    contact_ids = fields.One2many('sentinela.monitoring.contact', 'device_id', string='Contactos de Emergencia')
    
    # NUEVO: Configuracion personalizada de codigos por cuenta
    template_id = fields.Many2one('sentinela.alarm.code.template', string='Plantilla de Reacción')
    alarm_config_ids = fields.One2many('sentinela.device.alarm.config', 'device_id', string='Configuración de Eventos')

    # INTEGRACIÓN DE VIDEO (CCTV)
    has_video = fields.Boolean(string='Tiene Video Integrado', default=False)
    connection_mode = fields.Selection([
        ('direct', 'Directo (IP/Dominio)'),
        ('cloud', 'Nube (Número de Serie)')
    ], string='Modo de Conexión', default='cloud')
    
    dvr_brand = fields.Selection([
        ('hikvision', 'Hikvision / Epcom'),
        ('dahua', 'Dahua / Lorex'),
        ('generic', 'Genérico (RTSP)')
    ], string='Marca del DVR/NVR')
    
    dvr_serial = fields.Char(string='Número de Serie', help="ID único del equipo para conexión por nube.")
    dvr_ip = fields.Char(string='IP Pública / Dominio', help="Ej. 187.123.4.5 o sentinela.ddns.net")
    dvr_port = fields.Integer(string='Puerto HTTP/ISAPI', default=80)
    dvr_user = fields.Char(string='Usuario DVR')
    dvr_password = fields.Char(string='Password DVR')
    dvr_rtsp_port = fields.Integer(string='Puerto RTSP', default=554)

    _sql_constraints = [
        ('account_number_uniq', 'unique(account_number)', 'El número de cuenta del panel debe ser único.')
    ]

    def action_apply_template(self):
        """Copia la configuración de la plantilla a la cuenta del cliente"""
        self.ensure_one()
        if not self.template_id:
            return
        
        # 1. Borrar configuración actual
        self.alarm_config_ids.unlink()
        
        # 2. Clonar líneas de la plantilla
        vals_list = []
        for line in self.template_id.line_ids:
            vals_list.append({
                'device_id': self.id,
                'alarm_code_id': line.alarm_code_id.id,
                'priority_id': line.priority_id.id if line.priority_id else False,
                'notify_email': line.notify_email,
                'notify_telegram': line.notify_telegram,
            })
        
        if vals_list:
            self.env['sentinela.device.alarm.config'].create(vals_list)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Plantilla Aplicada',
                'message': f'Se han cargado {len(vals_list)} códigos desde la plantilla {self.template_id.name}',
                'sticky': False,
            }
        }
    
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
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MonitoringDevice(models.Model):
    _name = 'sentinela.monitoring.device'
    _description = 'Dispositivo de Monitoreo'
    _rec_name = 'device_id'

    device_id = fields.Char(string='ID Interno', required=True, default='New')
    account_number = fields.Char(
        string='Número de Cuenta (Panel)', required=True,
        default=lambda self: self._default_account_number(),
        help="Cuenta de 4 dígitos que envía el panel. Por defecto se sugiere el "
             "siguiente consecutivo libre; ajústalo si el panel ya tiene cuenta fija.")

    @api.model
    def _default_account_number(self):
        """Primer consecutivo de 4 dígitos no usado (0001, 0002, ...)."""
        used = set(self.search([]).mapped('account_number'))
        n = 1
        while n < 10000 and str(n).zfill(4) in used:
            n += 1
        return str(n).zfill(4)

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

    lot_id = fields.Many2one('stock.lot', string='Número de Serie / IMEI',
                            help="Seleccione el IMEI desde el inventario físico.")

    subscription_id = fields.Many2one(
        'sentinela.subscription',
        string='Suscripción',
        domain="[('id', 'in', allowed_subscription_ids)]",
        help="Suscripción de Monitoreo de Alarmas del cliente. Solo se listan las "
             "de ese cliente, de tipo alarma, vigentes y aún sin panel asignado."
    )
    allowed_subscription_ids = fields.Many2many(
        'sentinela.subscription', compute='_compute_allowed_subscription_ids',
        string='Suscripciones de alarma disponibles',
        help="Técnico: alimenta el dominio del campo Suscripción.")

    @api.depends('partner_id', 'subscription_id')
    def _compute_allowed_subscription_ids(self):
        """Subs candidatas: del cliente, tipo alarma, vigentes (no cerradas/
        canceladas) y SIN panel asignado. En edición agrega la sub ya ligada a
        este panel (queda fuera del filtro 'sin device' por ser su propio device)."""
        Sub = self.env['sentinela.subscription']
        for rec in self:
            if not rec.partner_id:
                rec.allowed_subscription_ids = Sub
                continue
            subs = Sub.search([
                ('partner_id', '=', rec.partner_id.id),
                ('service_type', '=', 'alarm'),
                ('state', 'not in', ('closed', 'cancelled')),
                ('monitoring_device_ids', '=', False),
            ])
            if rec.subscription_id:
                subs |= rec.subscription_id
            rec.allowed_subscription_ids = subs

    @api.constrains('subscription_id', 'partner_id')
    def _check_subscription_alarm(self):
        """Blindaje backend (el dominio es solo UI): la sub debe ser de alarma,
        del mismo cliente y no estar ya ligada a otro panel."""
        for rec in self:
            sub = rec.subscription_id
            if not sub:
                continue
            if sub.service_type != 'alarm':
                raise ValidationError(_(
                    "La suscripción %s no es de Monitoreo de Alarmas (es '%s'). "
                    "No se puede ligar a un panel."
                ) % (sub.name, sub.service_type))
            if sub.partner_id != rec.partner_id:
                raise ValidationError(_(
                    "La suscripción %s pertenece a otro cliente."
                ) % sub.name)
            otro = self.search([
                ('subscription_id', '=', sub.id), ('id', '!=', rec.id)], limit=1)
            if otro:
                raise ValidationError(_(
                    "La suscripción %s ya está ligada al panel %s."
                ) % (sub.name, otro.account_number))

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        """Si se selecciona un IMEI del inventario, usarlo como número de cuenta"""
        if self.lot_id:
            self.account_number = self.lot_id.name
            if not self.location and self.lot_id.product_id:
                self.notes = f"Equipo: {self.lot_id.product_id.display_name}"

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Al cambiar el cliente, limpia la suscripción si ya no le pertenece."""
        if self.subscription_id and self.subscription_id.partner_id != self.partner_id:
            self.subscription_id = False

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

    alarm_event_ids = fields.One2many('sentinela.alarm.event', 'device_id', string='Eventos de Alarma')
    alarm_signal_ids = fields.One2many('sentinela.alarm.signal', 'device_id', string='Señales de Alarma')
    zone_ids = fields.One2many('sentinela.monitoring.zone', 'device_id', string='Zonas Configuradas')
    contact_ids = fields.One2many('sentinela.monitoring.contact', 'device_id', string='Contactos de Emergencia')

    template_id = fields.Many2one('sentinela.alarm.code.template', string='Plantilla de Reacción')
    alarm_config_ids = fields.One2many('sentinela.device.alarm.config', 'device_id', string='Configuración de Eventos')

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
        ('account_number_uniq', 'unique(account_number)', 'El número de cuenta del panel debe ser único.'),
        ('subscription_uniq', 'unique(subscription_id)', 'Cada suscripción de alarma solo puede estar ligada a un panel.'),
    ]

    def action_apply_template(self):
        """Copia la configuración de la plantilla a la cuenta del cliente"""
        self.ensure_one()
        if not self.template_id:
            return
        self.alarm_config_ids.unlink()
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

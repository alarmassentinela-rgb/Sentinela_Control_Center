from odoo import models, fields, api

class AlarmSignal(models.Model):
    _name = 'sentinela.alarm.signal'
    _description = 'Señal de Alarma'
    _order = 'create_date desc'

    name = fields.Char(string='Referencia de la Señal', required=True, copy=False, readonly=True, default='Nuevo')
    signal_type = fields.Selection([
        ('alarm', 'Alarma'),
        ('supervision', 'Supervisión'),
        ('restore', 'Restauración'),
        ('trouble', 'Falla'),
        ('tamper', 'Manipulación'),
        ('low_battery', 'Batería Baja'),
        ('ac_loss', 'Pérdida de AC'),
        ('test', 'Prueba'),
        ('cancel', 'Cancelación'),
        ('auxiliary', 'Auxiliar'),
        ('fire', 'Fuego'),
        ('medical', 'Médica'),
        ('panic', 'Pánico'),
        ('duress', 'Coacción'),
        ('key_switch', 'Llave de Acceso'),
    ], string='Tipo de Señal', required=True)
    
    device_id = fields.Many2one('sentinela.monitoring.device', string='Dispositivo')
    account_number = fields.Char(string='Cuenta', related='device_id.account_number', store=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', related='device_id.partner_id', store=True)
    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción', related='device_id.subscription_id', store=True)

    priority_id = fields.Many2one('sentinela.alarm.priority', string='Prioridad')

    is_quarantine = fields.Boolean(string='En Cuarentena', default=False, index=True,
        help='Señal de cuenta no registrada. No genera evento ni dispositivo automáticamente; requiere revisión del operador.')
    quarantine_account = fields.Char(string='Cuenta Desconocida',
        help='Número de cuenta recibido del receptor pero no registrado como monitoring.device.')
    
    alarm_code = fields.Char(string='Código de Alarma', help="Ej. E130")
    zone = fields.Char(string='Zona', help="Ej. 001")
    
    description = fields.Text(string='Descripción')
    raw_data = fields.Text(string='Datos Crudos')
    
    received_date = fields.Datetime(string='Fecha de Recepción', default=fields.Datetime.now, required=True)
    processed_date = fields.Datetime(string='Fecha de Procesamiento')
    acknowledged_date = fields.Datetime(string='Fecha de Reconocimiento')
    resolved_date = fields.Datetime(string='Fecha de Resolución')
    
    status = fields.Selection([
        ('received', 'Recibida'),
        ('processing', 'Procesando'),
        ('acknowledged', 'Reconocida'),
        ('assigned', 'Asignada'),
        ('in_progress', 'En Progreso'),
        ('resolved', 'Resuelta'),
        ('closed', 'Cerrada'),
    ], string='Estado', default='received', required=True)
    
    assigned_operator_id = fields.Many2one('res.users', string='Operador Asignado')
    assigned_technician_id = fields.Many2one('res.users', string='Técnico Asignado')
    
    location = fields.Char(string='Ubicación', related='device_id.location', store=True)
    latitude = fields.Float(string='Latitud', related='device_id.latitude', store=True)
    longitude = fields.Float(string='Longitud', related='device_id.longitude', store=True)
    
    # Relación con eventos de alarma
    alarm_event_id = fields.Many2one('sentinela.alarm.event', string='Evento de Alarma')
    operator_notes = fields.Text(string='Notas del Operador')
    
    @api.model_create_multi
    def create(self, vals_list):
        if not vals_list: return super().create(vals_list)
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('sentinela.alarm.signal') or 'SIG-0000'
        
        signals = super().create(vals_list)
        # Notificar al Dashboard que hay tráfico nuevo
        if signals:
            self.env['bus.bus']._sendone('sentinela_monitoring', 'notification', {'type': 'refresh'})
        return signals

    def action_acknowledge(self):
        """Reconocer la señal"""
        self.write({
            'status': 'acknowledged',
            'acknowledged_date': fields.Datetime.now(),
            'assigned_operator_id': self.env.uid
        })

    def action_assign_technician(self):
        """Asignar técnico"""
        self.write({
            'status': 'assigned',
            'assigned_technician_id': self.env.uid
        })

    def action_mark_in_progress(self):
        """Marcar como en progreso"""
        self.write({
            'status': 'in_progress',
            'processed_date': fields.Datetime.now()
        })

    def action_resolve(self):
        """Resolver la señal"""
        self.write({
            'status': 'resolved',
            'resolved_date': fields.Datetime.now()
        })

    def action_close(self):
        """Cerrar la señal"""
        self.write({
            'status': 'closed'
        })

    def action_promote_to_device(self):
        """Convierte una señal en cuarentena en un monitoring.device real.
        Crea el device con la cuenta capturada y asocia la señal."""
        self.ensure_one()
        if not self.is_quarantine or not self.quarantine_account:
            return
        Device = self.env['sentinela.monitoring.device'].sudo()
        device = Device.search([('account_number', '=', self.quarantine_account)], limit=1)
        if not device:
            sub = self.env['sentinela.subscription'].sudo().search(
                [('monitoring_account_number', '=', self.quarantine_account)], limit=1)
            device = Device.create({
                'name': f"Manual {self.quarantine_account}",
                'account_number': self.quarantine_account,
                'partner_id': sub.partner_id.id if sub else 1,
                'status': 'active',
                'subscription_id': sub.id if sub else False,
            })
        self.write({
            'device_id': device.id,
            'is_quarantine': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sentinela.monitoring.device',
            'res_id': device.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_discard_quarantine(self):
        """Descarta señal en cuarentena (ruido / error)."""
        self.ensure_one()
        if not self.is_quarantine:
            return
        self.write({'status': 'closed'})

    def get_location_map_url(self):
        """Obtener URL para ver ubicación en mapa"""
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
        return None
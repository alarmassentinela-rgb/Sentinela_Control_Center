from odoo import models, fields, api

class AlarmEvent(models.Model):
    _name = 'sentinela.alarm.event'
    _description = 'Evento de Alarma'
    _inherit = ['mail.thread', 'mail.activity.mixin'] # Habilitar Auditoría y Chatter
    _order = 'start_date desc'

    name = fields.Char(string='Nombre del Evento', required=True)
    event_type = fields.Selection([
        ('burglary', 'Robo'),
        ('fire', 'Incendio'),
        ('medical', 'Emergencia Médica'),
        ('panic', 'Pánico'),
        ('duress', 'Coacción'),
        ('tamper', 'Manipulación'),
        ('trouble', 'Falla Técnica'),
        ('test', 'Prueba'),
        ('false_alarm', 'Falsa Alarma'),
        ('confirmed_alarm', 'Alarma Confirmada'),
        ('intrusion', 'Intrusión'),
        ('perimeter', 'Perímetro'),
        ('interior', 'Interior'),
        ('24_hour', '24 Horas'),
        ('day_night', 'Día/Noche'),
    ], string='Tipo de Evento', required=True)
    
    device_id = fields.Many2one('sentinela.monitoring.device', string='Dispositivo', required=True)
    account_number = fields.Char(string='Cuenta', related='device_id.account_number', store=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', related='device_id.partner_id', store=True)
    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción', related='device_id.subscription_id', store=True)
    service_address_id = fields.Many2one('res.partner', string='Dirección de Servicio', related='subscription_id.service_address_id', store=True)
    
    priority_id = fields.Many2one('sentinela.alarm.priority', string='Prioridad', required=True)
    alarm_code_id = fields.Many2one('sentinela.alarm.code', string='Código de Alarma')
    zone = fields.Char(string='Zona / Partición')
    
    start_date = fields.Datetime(string='Fecha de Inicio', default=fields.Datetime.now, required=True)
    end_date = fields.Datetime(string='Fecha de Finalización')
    duration = fields.Float(string='Duración (horas)', compute='_compute_duration', store=True)
    
    description = fields.Text(string='Descripción del Evento')
    resolution_notes = fields.Text(string='Notas de Resolución')
    
    status = fields.Selection([
        ('active', 'Activo'),
        ('acknowledged', 'Reconocido'),
        ('in_progress', 'En Progreso'),
        ('paused', 'En Pausa / Pendiente'),
        ('escalated', 'Escalado'),
        ('resolved', 'Resuelto'),
        ('closed', 'Cerrado'),
    ], string='Estado', default='active', required=True)
    
    assigned_operator_id = fields.Many2one('res.users', string='Operador Asignado')
    assigned_technician_id = fields.Many2one('res.users', string='Técnico Asignado')
    response_team_id = fields.Many2one('sentinela.response.team', string='Equipo de Respuesta')
    
    location = fields.Char(string='Ubicación', related='device_id.location', store=True)
    latitude = fields.Float(string='Latitud', related='device_id.latitude', store=True)
    longitude = fields.Float(string='Longitud', related='device_id.longitude', store=True)
    
    # Relación con señales de alarma
    alarm_signal_ids = fields.One2many('sentinela.alarm.signal', 'alarm_event_id', string='Señales Relacionadas')
    
    # Relación con órdenes de servicio FSM
    fsm_order_ids = fields.One2many('sentinela.fsm.order', 'alarm_event_id', string='Órdenes de Servicio')
    
    @api.model_create_multi
    def create(self, vals_list):
        events = super(AlarmEvent, self).create(vals_list)
        for event in events:
            # Determinar si debe sonar sirena (Por código o por nivel de prioridad >= 7)
            priority_level = event.priority_id.level if event.priority_id else 0
            play_sound = (event.alarm_code_id.play_sound if event.alarm_code_id else False) or (priority_level >= 7)
            
            # Notificar al bus para tiempo real
            self.env['bus.bus']._sendone('sentinela_monitoring', 'refresh', {
                'title': "ALERTA SENTINELA",
                'message': f"NUEVO EVENTO: {event.name}",
                'priority_level': priority_level,
                'event_id': event.id
            })
        return events
    
    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for event in self:
            if event.start_date and event.end_date:
                duration = event.end_date - event.start_date
                event.duration = duration.total_seconds() / 3600
            else:
                event.duration = 0.0

    def action_acknowledge(self):
        """Reconocer el evento"""
        self.write({
            'status': 'acknowledged',
            'assigned_operator_id': self.env.uid
        })

    def action_escalate(self):
        """Escalar el evento"""
        self.write({
            'status': 'escalated'
        })

    def action_assign_technician(self):
        """Asignar técnico"""
        self.write({
            'status': 'in_progress',
            'assigned_technician_id': self.env.uid
        })

    def action_resolve(self):
        """Resolver el evento"""
        self.write({
            'status': 'resolved',
            'end_date': fields.Datetime.now()
        })

    def action_close(self):
        """Cerrar el evento"""
        self.write({
            'status': 'closed'
        })

    def create_fsm_order(self):
        """Crear una orden de servicio FSM para responder al evento"""
        self.ensure_one()
        fsm_order_model = self.env['sentinela.fsm.order']
        
        # Generar Link de Google Maps
        maps_link = self.get_location_map_url() or "Sin coordenadas"
        
        # Descripción detallada para el patrullero
        instructions = f"""
🚨 ALARMA: {self.event_type.upper()}
📍 UBICACIÓN: {self.location or 'Dirección del cliente'}
🔗 MAPA: {maps_link}

📝 DETALLES:
{self.description or 'Sin detalles adicionales'}

⚠️ INSTRUCCIONES:
1. Llegar al sitio.
2. Verificar perímetro.
3. Tomar fotos de evidencia.
4. Contactar a central si se requiere apoyo policial.
"""

        # Determinar prioridad FSM basada en el nivel de la alarma (1-10)
        fsm_priority = '0'
        if self.priority_id:
            if self.priority_id.level >= 9:
                fsm_priority = '3' # Crítica
            elif self.priority_id.level >= 7:
                fsm_priority = '2' # Urgente
            elif self.priority_id.level >= 5:
                fsm_priority = '1' # Alta

        order_vals = {
            'partner_id': self.partner_id.id,
            'service_address_id': self.partner_id.id,
            'subscription_id': self.subscription_id.id,
            'description': instructions,
            'priority': fsm_priority,
            'service_type': 'repair', # O un tipo especifico 'patrol'
            'alarm_event_id': self.id,
            'scheduled_date': fields.Datetime.now()
        }
        
        fsm_order = fsm_order_model.create(order_vals)
        
        # Cambiar estado del evento a "En Progreso"
        self.write({'status': 'in_progress'})
        
        # Enviar notificación Push al técnico asignado (si lo hay) o al canal de patrulleros
        # (Aquí podríamos agregar lógica para buscar patrulleros disponibles)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orden de Patrullaje',
            'res_model': 'sentinela.fsm.order',
            'res_id': fsm_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def get_notification_emails(self):
        """Obtiene los correos configurados para recibir alertas de este cliente"""
        # Buscar contactos hijos con tipo 'other' o etiqueta 'Alarma'
        # Por simplicidad, tomamos el correo del cliente y sus contactos
        emails = []
        if self.partner_id.email:
            emails.append(self.partner_id.email)
        
        for child in self.partner_id.child_ids:
            if child.email:
                emails.append(child.email)
        return emails

    def get_location_map_url(self):
        """Obtener URL para ver ubicación en mapa"""
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
        return None
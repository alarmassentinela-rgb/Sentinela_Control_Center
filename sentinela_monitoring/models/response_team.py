from odoo import models, fields, api

class ResponseTeam(models.Model):
    _name = 'sentinela.response.team'
    _description = 'Equipo de Respuesta'
    _rec_name = 'name'

    name = fields.Char(string='Nombre del Equipo', required=True)
    description = fields.Text(string='Descripción')
    
    team_leader_id = fields.Many2one('res.users', string='Líder del Equipo', required=True)
    member_ids = fields.Many2many('res.users', string='Miembros del Equipo')
    
    capacity = fields.Integer(string='Capacidad (número de alarmas simultáneas)', default=1)
    response_area_ids = fields.Many2many('res.partner.category', string='Áreas de Respuesta')
    
    status = fields.Selection([
        ('available', 'Disponible'),
        ('busy', 'Ocupado'),
        ('offline', 'Fuera de Servicio'),
        ('on_call', 'De Guardia'),
    ], string='Estado', default='available', required=True)
    
    current_location_lat = fields.Float(string='Latitud Actual', digits=(10, 7))
    current_location_lon = fields.Float(string='Longitud Actual', digits=(10, 7))
    last_update = fields.Datetime(string='Última Actualización de Ubicación')
    
    active_incidents = fields.Integer(string='Incidentes Activos', compute='_compute_active_incidents')
    average_response_time = fields.Float(string='Tiempo Promedio de Respuesta (minutos)')
    
    alarm_event_ids = fields.One2many('sentinela.alarm.event', 'response_team_id', string='Eventos Asignados')
    
    @api.depends('alarm_event_ids')
    def _compute_active_incidents(self):
        for team in self:
            active_events = team.alarm_event_ids.filtered(lambda e: e.status in ['active', 'in_progress'])
            team.active_incidents = len(active_events)

    def action_go_available(self):
        """Marcar equipo como disponible"""
        self.write({'status': 'available'})

    def action_go_busy(self):
        """Marcar equipo como ocupado"""
        self.write({'status': 'busy'})

    def action_go_offline(self):
        """Marcar equipo como fuera de servicio"""
        self.write({'status': 'offline'})

    def action_on_call(self):
        """Marcar equipo como de guardia"""
        self.write({'status': 'on_call'})

    def assign_to_incident(self, incident_id):
        """Asignar equipo a un incidente"""
        incident_id.write({
            'assigned_technician_id': self.team_leader_id.id,
            'status': 'in_progress'
        })
        
        self.write({'status': 'busy'})
        
        # Enviar notificación al equipo
        for member in self.member_ids:
            incident_id.send_push_notification(
                title="Nuevo Incidente Asignado",
                message=f"El equipo {self.name} ha sido asignado al incidente {incident_id.name}",
                recipient_user=member,
                notification_type='assignment'
            )

    def update_location(self, lat, lon):
        """Actualizar ubicación del equipo"""
        self.write({
            'current_location_lat': lat,
            'current_location_lon': lon,
            'last_update': fields.Datetime.now()
        })

    def get_current_location_map_url(self):
        """Obtener URL para ver ubicación actual en mapa"""
        if self.current_location_lat and self.current_location_lon:
            return f"https://www.google.com/maps/search/?api=1&query={self.current_location_lat},{self.current_location_lon}"
        return None
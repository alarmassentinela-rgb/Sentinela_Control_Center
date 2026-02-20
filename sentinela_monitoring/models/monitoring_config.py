from odoo import models, fields, api

class MonitoringConfig(models.Model):
    _name = 'sentinela.monitoring.config'
    _description = 'Configuración Global de Monitoreo'

    name = fields.Char(string='Configuración', default='Ajustes de Central', readonly=True)
    
    # Audio Global
    pending_event_sound = fields.Binary(string='Audio de Eventos Pendientes', help="Archivo MP3/WAV que sonará mientras existan alarmas sin atender.")
    pending_event_sound_filename = fields.Char(string='Nombre del Archivo')
    
    # Parámetros de Operación
    refresh_interval = fields.Integer(string='Intervalo de Refresco (Segundos)', default=5)
    auto_escalate_minutes = fields.Integer(string='Tiempo para Escalado Automático (Min)', default=5)
    
    # Singleton pattern para asegurar que solo exista un registro
    @api.model
    def get_config(self):
        config = self.search([], limit=1)
        if not config:
            config = self.create({})
        return config

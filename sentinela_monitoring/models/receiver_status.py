from odoo import models, fields, api
from datetime import datetime, timedelta

class ReceiverStatus(models.Model):
    _name = 'sentinela.receiver.status'
    _description = 'Estado del Receptor de Alarmas'

    name = fields.Char(default='Receiver Status')
    last_heartbeat = fields.Datetime(string='Último Latido')
    status = fields.Selection([
        ('online', 'En Línea'),
        ('offline', 'Desconectado')
    ], compute='_compute_status', string='Estado')

    @api.depends('last_heartbeat')
    def _compute_status(self):
        for rec in self:
            if rec.last_heartbeat:
                # Si el ultimo latido fue hace menos de 30 segundos, esta online
                delta = fields.Datetime.now() - rec.last_heartbeat
                if delta.total_seconds() < 30:
                    rec.status = 'online'
                else:
                    rec.status = 'offline'
            else:
                rec.status = 'offline'

    @api.model
    def update_heartbeat(self):
        """Metodo llamado por el script receiver.py cada 10 segundos"""
        status_rec = self.search([], limit=1)
        if not status_rec:
            status_rec = self.create({'name': 'Main Receiver'})
        
        status_rec.write({'last_heartbeat': fields.Datetime.now()})
        return True

    @api.model
    def get_status(self):
        """Metodo para el Dashboard JS"""
        status_rec = self.search([], limit=1)
        if not status_rec:
            return {'state': 'offline', 'last_seen': 'Nunca'}
        
        # Calcular estado
        is_online = False
        if status_rec.last_heartbeat:
            delta = fields.Datetime.now() - status_rec.last_heartbeat
            is_online = delta.total_seconds() < 30
            
        # Formatear fecha para JS (zona horaria del usuario seria ideal, aqui va UTC string)
        return {
            'state': 'online' if is_online else 'offline',
            'last_seen': str(status_rec.last_heartbeat)
        }

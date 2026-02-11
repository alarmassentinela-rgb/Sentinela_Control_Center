from odoo import models, fields, api

class FSMNotification(models.Model):
    _name = 'sentinela.fsm.notification'
    _description = 'Notificaciones Push FSM'
    _order = 'create_date desc'

    order_id = fields.Many2one('sentinela.fsm.order', string='Orden de Servicio', required=True, ondelete='cascade')
    title = fields.Char(string='Título', required=True)
    message = fields.Text(string='Mensaje', required=True)
    recipient_user_id = fields.Many2one('res.users', string='Usuario Destinatario', required=True)
    sent_date = fields.Datetime(string='Fecha de Envío', default=fields.Datetime.now)
    is_read = fields.Boolean(string='Leído', default=False)
    notification_type = fields.Selection([
        ('assignment', 'Asignación'),
        ('start', 'Inicio de Trabajo'),
        ('pause', 'Pausa'),
        ('resume', 'Reanudación'),
        ('finish', 'Finalización'),
        ('update', 'Actualización'),
        ('reminder', 'Recordatorio')
    ], string='Tipo de Notificación', default='update')

    def mark_as_read(self):
        """Marcar notificación como leída"""
        self.write({'is_read': True})
        return True

    def mark_as_unread(self):
        """Marcar notificación como no leída"""
        self.write({'is_read': False})
        return True
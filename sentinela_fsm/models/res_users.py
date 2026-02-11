from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    fsm_notification_count = fields.Integer(
        string='Contador de Notificaciones FSM',
        compute='_compute_fsm_notification_count',
        store=False
    )
    
    def _compute_fsm_notification_count(self):
        for user in self:
            notifications = self.env['sentinela.fsm.notification'].search([
                ('recipient_user_id', '=', user.id),
                ('is_read', '=', False)
            ])
            user.fsm_notification_count = len(notifications)
    
    def get_unread_fsm_notifications(self):
        """Obtener notificaciones no leídas para este usuario"""
        return self.env['sentinela.fsm.notification'].search([
            ('recipient_user_id', '=', self.id),
            ('is_read', '=', False)
        ])
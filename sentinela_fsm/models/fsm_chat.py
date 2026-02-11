from odoo import models, fields, api

class FSMChatMessage(models.Model):
    _name = 'sentinela.fsm.chat.message'
    _description = 'Mensajes de Chat FSM'
    _order = 'create_date asc'

    order_id = fields.Many2one('sentinela.fsm.order', string='Orden de Servicio', required=True, ondelete='cascade')
    sender_id = fields.Many2one('res.partner', string='Remitente', required=True)
    receiver_id = fields.Many2one('res.partner', string='Destinatario', required=True)
    message = fields.Text(string='Mensaje', required=True)
    timestamp = fields.Datetime(string='Fecha/Hora', default=fields.Datetime.now)
    is_read = fields.Boolean(string='Leído', default=False)
    message_type = fields.Selection([
        ('text', 'Texto'),
        ('image', 'Imagen'),
        ('file', 'Archivo'),
        ('system', 'Sistema')
    ], string='Tipo de Mensaje', default='text')
    attachment_ids = fields.Many2many('ir.attachment', string='Archivos Adjuntos')

    @api.model
    def create_message(self, order_id, sender_id, receiver_id, message, message_type='text'):
        """Método para crear un nuevo mensaje de chat"""
        return self.create({
            'order_id': order_id,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'message': message,
            'message_type': message_type
        })

    def mark_as_read(self):
        """Marcar mensajes como leídos"""
        self.write({'is_read': True})
        return True

    def get_chat_messages(self, order_id):
        """Obtener todos los mensajes de un chat específico"""
        return self.search([('order_id', '=', order_id)], order='create_date asc')
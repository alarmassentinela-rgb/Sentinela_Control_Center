# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class FSMChatSendMessageWizard(models.TransientModel):
    _name = 'sentinela.fsm.chat.send.message.wizard'
    _description = 'Enviar Mensaje de Chat FSM'

    order_id = fields.Many2one('sentinela.fsm.order', string='Orden de Servicio', required=True)
    sender_id = fields.Many2one('res.partner', string='Remitente', required=True)
    receiver_id = fields.Many2one('res.partner', string='Destinatario', required=True)
    message = fields.Text(string='Mensaje', required=True)
    message_type = fields.Selection([
        ('text', 'Texto'),
        ('image', 'Imagen'),
        ('file', 'Archivo'),
        ('system', 'Sistema')
    ], string='Tipo de Mensaje', default='text')

    @api.model
    def default_get(self, fields):
        res = super(FSMChatSendMessageWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        
        if active_model == 'sentinela.fsm.order' and active_id:
            order = self.env['sentinela.fsm.order'].browse(active_id)
            res['order_id'] = order.id
            res['sender_id'] = order.technician_id.partner_id.id if order.technician_id else False
            res['receiver_id'] = order.partner_id.id
        
        return res

    def action_send_message(self):
        """Enviar mensaje de chat"""
        self.ensure_one()
        
        if self.order_id and self.sender_id and self.receiver_id and self.message:
            # Crear el mensaje de chat
            chat_message = self.env['sentinela.fsm.chat.message'].create({
                'order_id': self.order_id.id,
                'sender_id': self.sender_id.id,
                'receiver_id': self.receiver_id.id,
                'message': self.message,
                'message_type': self.message_type or 'text'
            })
            
            # Agregar mensaje al chatter de la orden
            self.order_id.message_post(
                body=f"<b>Nuevo mensaje de chat:</b> {self.message}",
                subtype_xmlid='mail.mt_note',
                message_type='notification'
            )
        
        return {'type': 'ir.actions.act_window_close'}
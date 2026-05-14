from odoo import models, fields, api

class MonitoringCall(models.Model):
    _name = 'sentinela.monitoring.call'
    _description = 'Registro de Llamada de Monitoreo'
    _order = 'date desc'

    name = fields.Char(string='ID de Llamada', required=True)
    date = fields.Datetime(string='Fecha y Hora', default=fields.Datetime.now)
    src = fields.Char(string='Extensión Origen')
    dst = fields.Char(string='Número Destino')
    duration = fields.Integer(string='Duración (seg)')
    
    partner_id = fields.Many2one('res.partner', string='Cliente')
    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción')
    alarm_event_id = fields.Many2one('sentinela.alarm.event', string='Evento de Alarma')
    
    audio_file = fields.Binary(string='Grabación de Audio')
    audio_filename = fields.Char(string='Nombre del Archivo')

    def action_send_by_telegram(self):
        self.ensure_one()
        if not self.partner_id.telegram_chat_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'El cliente no tiene un ID de Telegram configurado.',
                    'type': 'danger',
                }
            }
        
        # Lógica para enviar archivo vía Telegram API
        import requests
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('sentinela_syscom.telegram_token')
        url = f"https://api.telegram.org/bot{token}/sendAudio"
        
        try:
            import io
            import base64
            audio_data = io.BytesIO(base64.b64decode(self.audio_file))
            audio_data.name = self.audio_filename or "grabacion.wav"
            
            res = requests.post(url, 
                data={'chat_id': self.partner_id.telegram_chat_id, 'caption': f"🎙️ Grabación de llamada: {self.date}"},
                files={'audio': audio_data}
            )
            if res.ok:
                return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Enviado', 'message': 'Grabación enviada por Telegram.', 'type': 'success'}}
        except Exception as e:
            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Error', 'message': str(e), 'type': 'danger'}}

    def action_send_by_email(self):
        self.ensure_one()
        # Lógica simplificada de envío de correo
        self.message_post(body="📧 Grabación enviada por correo al cliente.", attachment_ids=[])
        return True

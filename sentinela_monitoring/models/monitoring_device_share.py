from odoo import models, fields, api
import uuid
from datetime import datetime, timedelta

class MonitoringDeviceShare(models.Model):
    _name = 'sentinela.monitoring.device.share'
    _description = 'Enlace de Seguimiento Temporal (Cuenta Espejo)'

    device_id = fields.Many2one('sentinela.monitoring.device', string='Vehículo', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Generado por', default=lambda self: self.env.user.partner_id)
    
    token = fields.Char(string='Token de Acceso', readonly=True, default=lambda self: str(uuid.uuid4()))
    
    expiration_date = fields.Datetime(string='Fecha de Expiración', required=True, 
                                     default=lambda self: fields.Datetime.now() + timedelta(hours=24))
    
    is_active = fields.Boolean(string='Activo', compute='_compute_is_active', store=True)
    
    share_url = fields.Char(string='URL de Seguimiento', compute='_compute_share_url')
    
    recipient_name = fields.Char(string='Nombre del Cliente Final')
    notes = fields.Text(string='Notas del Viaje')

    @api.depends('expiration_date')
    def _compute_is_active(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_active = record.expiration_date > now

    def _compute_share_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.share_url = f"{base_url}/senticar/share/{record.token}"

    def action_send_whatsapp(self):
        """ Genera el link y prepara el mensaje de WhatsApp """
        self.ensure_one()
        msg = "🚚 *Seguimiento de su Mercancía (SentiCar)*\n\n"
        msg += f"Hola {self.recipient_name or 'Cliente'},\n"
        msg += f"Le compartimos el link para seguir el trayecto de la unidad *{self.device_id.name}* en tiempo real.\n\n"
        msg += f"🧭 *Link:* {self.share_url}\n"
        msg += f"⚠️ *Vence:* {self.expiration_date}\n\n"
        msg += "Buen viaje."
        
        import urllib.parse
        encoded_msg = urllib.parse.quote(msg)
        
        return {
            'type': 'ir.actions.act_url',
            'url': f"https://wa.me/?text={encoded_msg}",
            'target': 'new',
        }

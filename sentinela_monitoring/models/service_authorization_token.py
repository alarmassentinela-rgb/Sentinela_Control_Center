"""F2.7.1 — Token de autorización web para servicios no incluidos en plan.

Cliente recibe Telegram con un magic link. Click → página pública que muestra
el monto y permite AUTORIZAR o RECHAZAR. La respuesta queda registrada con
timestamp + IP + User-Agent → evidencia legal.
"""
import logging
import secrets

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ServiceAuthorizationToken(models.Model):
    _name = 'sentinela.service.authorization.token'
    _description = 'Token de autorización de servicio extra'
    _order = 'create_date desc'
    _rec_name = 'token'

    alarm_event_id = fields.Many2one('sentinela.alarm.event', required=True, ondelete='cascade',
                                      string='Evento de Alarma')
    partner_id = fields.Many2one('res.partner', string='Cliente',
                                  related='alarm_event_id.partner_id', store=True)
    service_type = fields.Selection([
        ('patrol', 'Patrullaje'),
        ('maintenance', 'Mantenimiento'),
        ('night_unit', 'Unidad nocturna'),
    ], required=True, default='patrol', string='Servicio')

    token = fields.Char(string='Token', required=True, copy=False, readonly=True,
                        default=lambda self: secrets.token_urlsafe(32),
                        index=True)
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('authorized', 'Autorizado'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Cancelado'),
    ], default='pending', required=True, string='Estado')

    amount = fields.Float(string='Monto ($)', help='Costo del servicio sin IVA.')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    telegram_sent = fields.Boolean(string='Telegram enviado', readonly=True)
    telegram_sent_at = fields.Datetime(string='Telegram enviado el', readonly=True)
    telegram_message = fields.Text(string='Mensaje enviado', readonly=True)

    responded_at = fields.Datetime(string='Respondido el', readonly=True)
    response_ip = fields.Char(string='IP del cliente', readonly=True)
    response_user_agent = fields.Char(string='User-Agent', readonly=True)

    notes = fields.Text(string='Notas')

    _sql_constraints = [
        ('token_unique', 'unique(token)', 'El token debe ser único.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        # secrets ya genera token en default, pero por si acaso defensivo
        for vals in vals_list:
            if not vals.get('token'):
                vals['token'] = secrets.token_urlsafe(32)
        return super().create(vals_list)

    def get_authorization_url(self):
        """URL completa que se envía al cliente vía Telegram."""
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        return f"{base}/sentinela/autorizar/{self.token}"

    def action_send_telegram(self):
        """F2.7.1 + F3 — Manda el magic link al cliente por su canal preferido
        (notification_channel: telegram y/o whatsapp)."""
        self.ensure_one()
        partner = self.partner_id
        # Verificar que hay al menos un canal disponible
        ch = partner.notification_channel or 'both'
        has_tg = ch in ('telegram', 'both') and partner.telegram_chat_id
        has_wa = ch in ('whatsapp', 'both') and (partner.whatsapp_number or partner.mobile or partner.phone)
        if not has_tg and not has_wa:
            raise UserError(_(
                "El cliente %s no tiene canal disponible (notification_channel=%s, "
                "telegram_chat_id=%s, mobile=%s). Captura datos o usa autorización manual."
            ) % (partner.name, ch, bool(partner.telegram_chat_id), bool(partner.mobile)))
        url = self.get_authorization_url()
        service_name = dict(self._fields['service_type'].selection).get(self.service_type, self.service_type)
        msg = (
            f"🚨 *SENTINELA: AUTORIZACIÓN REQUERIDA*\n\n"
            f"Hola *{partner.name}*, se activó una alarma en su domicilio.\n\n"
            f"Para enviar el servicio de *{service_name}* a verificar, su plan "
            f"requiere autorización del costo aparte:\n\n"
            f"💰 *Costo:* ${self.amount:,.2f} {self.currency_id.name or 'MXN'} (sin IVA)\n"
            f"📋 *Evento:* {self.alarm_event_id.name}\n\n"
            f"👉 Para AUTORIZAR o RECHAZAR haga click aquí:\n{url}\n\n"
            f"_Su respuesta queda registrada con fecha, hora y dispositivo para "
            f"efectos de comprobación del consentimiento._"
        )
        res = partner.notify(message=msg)
        any_sent = any(res.values())
        self.write({
            'telegram_sent': bool(res.get('telegram')) or bool(res.get('whatsapp')),
            'telegram_sent_at': fields.Datetime.now() if any_sent else False,
            'telegram_message': msg,
        })
        channels_sent = [c for c, ok in res.items() if ok]
        self.alarm_event_id.message_post(body=_(
            "Autorización enviada al cliente (token %s) — canales: %s."
        ) % (self.token[:8], ', '.join(channels_sent) or 'NINGUNO'))
        return any_sent

    def _record_response(self, ip=None, user_agent=None):
        """Helper para registrar IP/UA al responder."""
        self.write({
            'responded_at': fields.Datetime.now(),
            'response_ip': ip or '',
            'response_user_agent': (user_agent or '')[:255],
        })

    def authorize(self, ip=None, user_agent=None):
        """Marca como autorizado y dispara el flujo de cobranza del evento."""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("Este token ya fue %s, no se puede autorizar de nuevo.") % self.state)
        self._record_response(ip, user_agent)
        self.state = 'authorized'
        # Dispara action_authorize_service del evento (que crea sale.order F2.6)
        self.alarm_event_id.action_authorize_service()
        self.alarm_event_id.message_post(body=_(
            "Cliente AUTORIZÓ servicio extra vía web (token %s) desde IP %s."
        ) % (self.token[:8], ip or 'desconocida'))
        return True

    def reject(self, ip=None, user_agent=None):
        """Marca como rechazado. NO dispara cobranza ni cierra evento — el
        operador decide qué hacer (típicamente cerrar con
        close_reason='cliente_rechazo_servicio')."""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("Este token ya fue %s, no se puede rechazar de nuevo.") % self.state)
        self._record_response(ip, user_agent)
        self.state = 'rejected'
        self.alarm_event_id.message_post(body=_(
            "Cliente RECHAZÓ servicio extra vía web (token %s) desde IP %s."
        ) % (self.token[:8], ip or 'desconocida'))
        return True

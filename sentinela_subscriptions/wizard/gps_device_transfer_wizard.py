from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GpsDeviceTransfer(models.TransientModel):
    """Asistente para mover un equipo GPS de una suscripción a otra (p.ej. de la cuenta maestra
    de Sentinela a la suscripción del cliente que lo compró). El equipo se reapunta: conserva su
    device en SentiCar (mismo IMEI/historial), pasa a verse en la cuenta del cliente destino y deja
    de verse en la de origen."""
    _name = 'sentinela.gps.device.transfer'
    _description = 'Transferir equipo GPS a otra suscripción'

    device_id = fields.Many2one('sentinela.subscription.gps.device', string='Equipo',
                                required=True, ondelete='cascade')
    source_subscription_id = fields.Many2one(related='device_id.subscription_id',
                                             string='Suscripción actual', readonly=True)
    source_partner_id = fields.Many2one(related='device_id.subscription_id.partner_id',
                                        string='Cliente actual', readonly=True)
    gps_platform = fields.Selection(related='device_id.gps_platform', readonly=True)
    gps_mode = fields.Selection(related='device_id.gps_mode', readonly=True)

    target_subscription_id = fields.Many2one(
        'sentinela.subscription', string='Suscripción destino', required=True,
        domain="[('service_type', '=', 'gps'),"
               " ('gps_platform', '=', gps_platform),"
               " ('gps_mode', '=', gps_mode),"
               " ('id', '!=', source_subscription_id)]",
        help="Suscripción de GPS del cliente que recibirá el equipo. Debe ser de la misma "
             "plataforma y modo (vehículo/móvil) que el equipo.")
    target_partner_id = fields.Many2one(related='target_subscription_id.partner_id',
                                        string='Cliente destino', readonly=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.target_subscription_id:
            raise UserError(_("Selecciona la suscripción destino."))
        self.device_id.transfer_to_subscription(self.target_subscription_id)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Suscripción destino'),
            'res_model': 'sentinela.subscription',
            'res_id': self.target_subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

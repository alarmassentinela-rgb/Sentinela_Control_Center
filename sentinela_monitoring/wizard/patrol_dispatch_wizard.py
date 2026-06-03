from odoo import models, fields, api, _


class PatrolDispatchWizard(models.TransientModel):
    _name = 'sentinela.patrol.dispatch.wizard'
    _description = 'Enviar Patrullero al Domicilio'

    alarm_event_id = fields.Many2one('sentinela.alarm.event', string='Evento de Alarma', required=True)
    partner_id = fields.Many2one('res.partner', string='Cliente',
        related='alarm_event_id.partner_id', readonly=True)
    account_number = fields.Char(string='Cuenta', related='alarm_event_id.account_number', readonly=True)
    address = fields.Char(string='Domicilio', compute='_compute_address', readonly=True)

    technician_id = fields.Many2one('res.users', string='Patrullero',
        required=True, domain="[('is_patrol', '=', True)]",
        help='Usuario marcado como Patrulla (is_patrol). Su dispositivo Traccar permite el rastreo en vivo.')
    notes = fields.Text(string='Instrucciones para el patrullero',
        help='Se anexan a la descripción de la orden (opcional).')

    @api.depends('alarm_event_id')
    def _compute_address(self):
        for w in self:
            dev = w.alarm_event_id.device_id
            w.address = (dev.location if dev else False) or (w.partner_id.contact_address or '')

    def action_dispatch(self):
        """Despacha al patrullero: crea la orden de patrullaje ASIGNADA con la
        info del evento + coordenadas del cliente, y le notifica (push).
        El cliente NO se notifica aquí: eso ocurre cuando el patrullero
        confirma 'Ya salí' desde su app (fsm_order.action_start)."""
        self.ensure_one()
        event = self.alarm_event_id

        # Reutiliza el constructor idempotente del evento (descripción rica + coords).
        order_id = event.create_fsm_order(technician_id=self.technician_id.id, service_type='patrol')
        order = self.env['sentinela.fsm.order'].browse(order_id)

        # Anexar instrucciones del operador, si las hay.
        if self.notes:
            order.sudo().write({
                'description': (order.description or '') +
                    f"<br/><b>📋 Instrucciones de la central:</b><br/>{self.notes}",
            })

        # Notificar al patrullero (push + correo de asignación).
        # Solo si la orden quedó realmente asignada (no era un duplicado ya en proceso).
        if order.stage == 'assigned':
            order.action_assign()

        event.message_post(body=_(
            "🚓 Patrullero <b>%s</b> despachado. Orden %s asignada. "
            "El cliente será notificado cuando el patrullero confirme su salida."
        ) % (self.technician_id.name, order.name))

        # Abrir la orden para que el operador la monitoree.
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orden de Patrullaje'),
            'res_model': 'sentinela.fsm.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

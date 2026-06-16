from odoo import models, fields, api, _


class PatrolDispatchWizard(models.TransientModel):
    _name = 'sentinela.patrol.dispatch.wizard'
    _description = 'Enviar Patrullero al Domicilio'

    alarm_event_id = fields.Many2one('sentinela.alarm.event', string='Evento de Alarma', required=True)
    partner_id = fields.Many2one('res.partner', string='Cliente',
        related='alarm_event_id.partner_id', readonly=True)
    account_number = fields.Char(string='Cuenta', related='alarm_event_id.account_number', readonly=True)
    address = fields.Char(string='Domicilio', compute='_compute_address', readonly=True)

    patrol_agent_id = fields.Many2one('res.partner', string='Quién atiende (turno)',
        domain="[('is_patrol', '=', True)]",
        help='Persona del catálogo de Patrulleros que sale esta vez. Para que alguien '
             'aparezca aquí, marca su contacto como "Es Patrulla" (puede ser patrullero, '
             'técnico, vendedor o admin). Opcional.')
    patrol_unit_id = fields.Many2one('sentinela.patrol.unit', string='Unidad a rastrear',
        required=True, domain="[('available', '=', True)]",
        default=lambda self: self.env['sentinela.patrol.unit']._get_default_dispatch_unit().id,
        help='Dispositivo SentiCar que se rastreará: el celular compartido del turno o un '
             'vehículo del catálogo. Se autoselecciona el de despacho por defecto; cámbialo '
             'si hoy salen en otra unidad.')
    notes = fields.Text(string='Instrucciones para el patrullero',
        help='Se anexan a la descripción de la orden (opcional).')

    @api.onchange('patrol_agent_id')
    def _onchange_agent_default_unit(self):
        """Si quien atiende tiene una unidad fija propia, la prefiere; si no, deja
        la unidad por defecto de despacho (el celular compartido)."""
        for w in self:
            person_unit = w.patrol_agent_id.default_patrol_unit_id
            if person_unit:
                w.patrol_unit_id = person_unit

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
        order_id = event.create_fsm_order(
            service_type='patrol',
            patrol_unit_id=self.patrol_unit_id.id or None,
            patrol_agent_id=self.patrol_agent_id.id or None)
        order = self.env['sentinela.fsm.order'].browse(order_id)
        # Si la orden ya existía (idempotente) y el operador eligió otra unidad/agente, actualiza.
        upd = {}
        if self.patrol_unit_id and order.patrol_unit_id != self.patrol_unit_id:
            upd['patrol_unit_id'] = self.patrol_unit_id.id
        if self.patrol_agent_id and order.patrol_agent_id != self.patrol_agent_id:
            upd['patrol_agent_id'] = self.patrol_agent_id.id
        if upd:
            order.sudo().write(upd)

        # Anexar instrucciones del operador, si las hay.
        if self.notes:
            order.sudo().write({
                'description': (order.description or '') +
                    f"<br/><b>📋 Instrucciones de la central:</b><br/>{self.notes}",
            })

        # Push + correo SOLO si el agente es usuario del sistema (action_assign lo exige).
        # Si es solo contacto del catálogo, la orden ya quedó 'assigned' en create_fsm_order
        # y el operador la monitorea desde central.
        if order.technician_id and order.stage == 'assigned':
            order.action_assign()

        quien = self.patrol_agent_id.name or "turno"
        event.message_post(body=_(
            "🚓 Patrulla despachada (%s) — unidad <b>%s</b>. Orden %s. "
            "El cliente será notificado cuando se confirme la salida."
        ) % (quien, self.patrol_unit_id.name or '—', order.name))

        # Abrir la orden para que el operador la monitoree.
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orden de Patrullaje'),
            'res_model': 'sentinela.fsm.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

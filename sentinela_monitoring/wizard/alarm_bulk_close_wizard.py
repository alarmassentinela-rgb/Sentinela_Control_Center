from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AlarmBulkCloseWizard(models.TransientModel):
    _name = 'sentinela.alarm.bulk.close.wizard'
    _description = 'Cierre en bloque de eventos de alarma'

    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    event_ids = fields.Many2many('sentinela.alarm.event', string='Eventos a cerrar')
    event_count = fields.Integer(compute='_compute_event_count', string='Total')
    close_reason = fields.Selection([
        ('false_alarm', 'Falsa alarma'),
        ('user_error', 'Error de usuario'),
        ('customer_confirmed_ok', 'Cliente confirma OK'),
        ('verified_real', 'Evento real verificado'),
        ('patrol_no_event', 'Patrulla acudió, sin evento'),
        ('patrol_event', 'Patrulla acudió, evento confirmado'),
        ('no_contact', 'Sin contacto con cliente'),
        ('technical_fault', 'Falla técnica del equipo'),
        ('test_signal', 'Señal de prueba'),
        ('auto_offline_recovered', 'Panel offline recuperado (auto)'),
        ('cliente_rechazo_servicio', 'Cliente rechazó servicio extra'),
        ('other', 'Otro (especificar en notas)'),
    ], string='Motivo de cierre', required=True)
    resolution_notes = fields.Text(string='Notas de resolución')

    @api.depends('event_ids')
    def _compute_event_count(self):
        for w in self:
            w.event_count = len(w.event_ids)

    @api.constrains('event_ids')
    def _check_same_partner(self):
        """Candado: todos los eventos deben ser del MISMO cliente — evita cerrar
        por error eventos de otra cuenta."""
        for w in self:
            partners = w.event_ids.mapped('partner_id')
            if len(partners) > 1:
                raise ValidationError(_(
                    "Hay eventos de varios clientes seleccionados: %s. "
                    "Cierra en bloque solo eventos de UN cliente."
                ) % ', '.join(partners.mapped('name')))

    def action_close_bulk(self):
        self.ensure_one()
        if not self.event_ids:
            raise UserError(_("No hay eventos para cerrar."))
        if self.close_reason == 'other' and not (self.resolution_notes or '').strip():
            raise UserError(_("El motivo 'Otro' requiere especificar notas."))
        self._check_same_partner()
        uid = self.env.uid
        cerrados = 0
        saltados = []
        for ev in self.event_ids:
            if ev.status in ('resolved', 'closed'):
                continue
            # Respetar el mutex: no pisar un evento tomado por OTRO operador
            if ev.current_operator_id and ev.current_operator_id.id != uid:
                saltados.append('%s (%s)' % (ev.name, ev.current_operator_id.name))
                continue
            ev.write({
                'close_reason': self.close_reason,
                'resolution_notes': self.resolution_notes or ev.resolution_notes or '',
                'status': 'resolved',
                'end_date': fields.Datetime.now(),
                'current_operator_id': False,
                'claimed_at': False,
            })
            ev.message_post(body=_("Cerrado en bloque por %s (motivo: %s).") % (
                self.env.user.name,
                dict(self._fields['close_reason'].selection).get(self.close_reason)))
            cerrados += 1
        msg = _("%d evento(s) cerrado(s).") % cerrados
        if saltados:
            msg += _(" %d en atención por otro operador (no cerrados): %s") % (
                len(saltados), ', '.join(saltados))
        # refrescar dashboard
        self.env['bus.bus']._sendone('sentinela_monitoring', 'sentinela_monitoring', {'refresh': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cierre en bloque'),
                'message': msg,
                'type': 'success' if not saltados else 'warning',
                'sticky': bool(saltados),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

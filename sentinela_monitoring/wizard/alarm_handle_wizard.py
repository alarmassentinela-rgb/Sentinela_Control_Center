from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class AlarmWizardContactAttempt(models.TransientModel):
    _name = 'sentinela.alarm.wizard.contact.attempt'
    _description = 'Intento de contacto en wizard de alarma'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('sentinela.alarm.handle.wizard', ondelete='cascade', required=True)
    contact_id = fields.Many2one('sentinela.monitoring.contact', required=True)
    sequence = fields.Integer(default=10)
    contact_name = fields.Char(related='contact_id.name', readonly=True)
    contact_phone = fields.Char(related='contact_id.phone', readonly=True)
    relation = fields.Char(related='contact_id.relation', readonly=True)
    status = fields.Selection([
        ('not_tried', 'No intentado'),
        ('no_answer', 'No contestó'),
        ('reached_ok', 'Contactado · todo OK'),
        ('reached_alarm', 'Contactado · reporta alarma'),
        ('unavailable', 'Número no disponible'),
    ], default='not_tried', required=True)
    attempt_notes = fields.Char(string='Notas')


class AlarmHandleWizard(models.TransientModel):
    _name = 'sentinela.alarm.handle.wizard'
    _description = 'Centro de Control de Alarma'

    alarm_event_id = fields.Many2one('sentinela.alarm.event', string='Evento', readonly=True, required=True)
    partner_id = fields.Many2one('res.partner', related='alarm_event_id.partner_id', string='Cliente')
    account_number = fields.Char(related='alarm_event_id.account_number', string='Cuenta')
    priority_id = fields.Many2one(related='alarm_event_id.priority_id', string='Prioridad')

    # F2.4 — stepper
    state = fields.Selection([
        ('verify', '1. Verificar'),
        ('contact', '2. Contactar'),
        ('dispatch', '3. Despachar'),
        ('close', '4. Cierre'),
    ], default='verify', required=True, string='Paso')

    address_display = fields.Char(string='Dirección', compute='_compute_site_info')
    site_phone = fields.Char(string='Teléfono Sitio', compute='_compute_site_info')
    google_maps_link = fields.Char(string='Mapa')
    contact_ids = fields.Many2many('sentinela.monitoring.contact', compute='_compute_contacts',
                                    string='Contactos a Llamar')
    recent_signal_ids = fields.Many2many('sentinela.alarm.signal', compute='_compute_signals',
                                          string='Señales')

    # Step 2 — tracking de contactos
    contact_attempt_ids = fields.One2many('sentinela.alarm.wizard.contact.attempt', 'wizard_id',
                                           string='Intentos de Contacto')

    # Step 3 — tracking de despacho
    patrol_dispatched = fields.Boolean(string='Patrulla Despachada')
    fsm_order_created = fields.Boolean(string='Orden Técnica Creada')
    authorities_called = fields.Boolean(string='Autoridades Notificadas')
    dispatch_notes = fields.Text(string='Detalles de despacho')

    # Step 4 — cierre
    close_reason = fields.Selection(
        related='alarm_event_id.close_reason', readonly=False, string='Motivo de Cierre')
    final_notes = fields.Text(string='Notas Finales',
        help='Notas que se guardarán en resolution_notes del evento.')

    notes = fields.Text(string='Bitácora del Operador')
    extra_service_authorized = fields.Boolean(related='alarm_event_id.extra_service_authorized')
    patrol_included = fields.Boolean(default=False)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        event_id = self.env.context.get('default_alarm_event_id') or vals.get('alarm_event_id')
        if event_id:
            event = self.env['sentinela.alarm.event'].browse(event_id)
            # Auto-acknowledge al abrir wizard (claim + acknowledged_at + status)
            if event.status == 'active':
                event.action_acknowledge()
            # Precargar intentos de contacto desde los contactos de emergencia del device
            contacts = self.env['sentinela.monitoring.contact'].search([
                ('device_id', '=', event.device_id.id),
                ('is_emergency_contact', '=', True),
            ], order='user_number')
            if 'contact_attempt_ids' in fields_list and contacts:
                vals['contact_attempt_ids'] = [
                    (0, 0, {'contact_id': c.id, 'sequence': (i + 1) * 10})
                    for i, c in enumerate(contacts)
                ]
        return vals

    @api.depends('alarm_event_id')
    def _compute_site_info(self):
        for rec in self:
            dev = rec.alarm_event_id.device_id
            rec.address_display = dev.location or "Sin dirección registrada"
            rec.site_phone = "Consultar Ficha"

    @api.depends('alarm_event_id')
    def _compute_contacts(self):
        for rec in self:
            rec.contact_ids = self.env['sentinela.monitoring.contact'].search([
                ('device_id', '=', rec.alarm_event_id.device_id.id),
                ('is_emergency_contact', '=', True)
            ])

    @api.depends('alarm_event_id')
    def _compute_signals(self):
        for rec in self:
            rec.recent_signal_ids = self.env['sentinela.alarm.signal'].search([
                ('device_id', '=', rec.alarm_event_id.device_id.id)
            ], limit=5, order='id desc')

    # ---------- Navegación ----------

    _STATE_ORDER = ['verify', 'contact', 'dispatch', 'close']

    def action_next_step(self):
        self.ensure_one()
        idx = self._STATE_ORDER.index(self.state)
        if idx < len(self._STATE_ORDER) - 1:
            self.state = self._STATE_ORDER[idx + 1]
        return True

    def action_prev_step(self):
        self.ensure_one()
        idx = self._STATE_ORDER.index(self.state)
        if idx > 0:
            self.state = self._STATE_ORDER[idx - 1]
        return True

    # ---------- Atajos de cierre rápido ----------

    def action_shortcut_false_alarm(self):
        self.ensure_one()
        self.write({'state': 'close', 'close_reason': 'false_alarm'})
        return True

    def action_shortcut_customer_ok(self):
        self.ensure_one()
        self.write({'state': 'close', 'close_reason': 'customer_confirmed_ok'})
        return True

    # ---------- Acciones de despacho (compatibilidad con existentes) ----------

    def action_request_patrol_from_wizard(self):
        self.ensure_one()
        # Marca tracking + delega al método del evento si existe
        self.patrol_dispatched = True
        if hasattr(self.alarm_event_id, 'action_request_service_authorization'):
            return self.alarm_event_id.action_request_service_authorization('patrol')
        return True

    def action_dispatch_patrol(self):
        self.ensure_one()
        self.patrol_dispatched = True
        return True

    def action_create_technical_ticket(self):
        self.ensure_one()
        self.fsm_order_created = True
        return True

    def action_open_maps(self):
        return True

    # ---------- Cierre / Pausa / Cancelar ----------

    def _consolidate_bitacora(self):
        """Junta las notas del operador con los intentos de contacto en
        resolution_notes del evento, para auditoría."""
        self.ensure_one()
        parts = []
        if self.notes:
            parts.append(f"Bitácora:\n{self.notes}")
        attempted = self.contact_attempt_ids.filtered(lambda a: a.status != 'not_tried')
        if attempted:
            lines = [f"  · {a.contact_name} ({a.relation or 'sin relación'}): {dict(a._fields['status'].selection).get(a.status)}"
                     + (f" — {a.attempt_notes}" if a.attempt_notes else "")
                     for a in attempted]
            parts.append("Contactos intentados:\n" + "\n".join(lines))
        if self.dispatch_notes:
            parts.append(f"Despacho:\n{self.dispatch_notes}")
        flags = []
        if self.patrol_dispatched: flags.append('patrulla')
        if self.fsm_order_created: flags.append('orden técnica')
        if self.authorities_called: flags.append('autoridades')
        if flags:
            parts.append(f"Acciones tomadas: {', '.join(flags)}")
        if self.final_notes:
            parts.append(f"Cierre:\n{self.final_notes}")
        return "\n\n".join(parts) if parts else ""

    def action_finalize(self):
        """Cierra el evento: setea resolution_notes consolidado y llama action_resolve."""
        self.ensure_one()
        if not self.close_reason:
            raise UserError(_("Selecciona el motivo de cierre antes de finalizar."))
        bitacora = self._consolidate_bitacora()
        if bitacora:
            self.alarm_event_id.resolution_notes = bitacora
        # action_resolve valida close_reason y libera el lock
        self.alarm_event_id.action_resolve()
        return {'type': 'ir.actions.act_window_close'}

    def action_pause_event(self):
        self.ensure_one()
        bitacora = self._consolidate_bitacora()
        vals = {'status': 'paused'}
        if bitacora:
            vals['resolution_notes'] = bitacora
        self.alarm_event_id.with_context(mail_notrack=True).write(vals)
        return {'type': 'ir.actions.act_window_close'}

    # Compatibilidad con vista vieja (botón "Finalizar y Cerrar")
    def action_close_event(self):
        return self.action_finalize()

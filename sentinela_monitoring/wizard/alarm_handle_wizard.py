from odoo import models, fields, api, _
from datetime import datetime

class AlarmHandleWizard(models.TransientModel):
    _name = 'sentinela.alarm.handle.wizard'
    _description = 'Centro de Control de Alarma'

    alarm_event_id = fields.Many2one('sentinela.alarm.event', string='Evento', readonly=True)
    partner_id = fields.Many2one('res.partner', related='alarm_event_id.partner_id', string='Cliente')
    service_address_id = fields.Many2one('res.partner', related='alarm_event_id.service_address_id', string='Dirección de Servicio')
    account_number = fields.Char(related='alarm_event_id.account_number', string='Cuenta')
    
    address_display = fields.Char(string='Dirección Completa', compute='_compute_site_info')
    site_phone = fields.Char(string='Teléfono del Sitio', compute='_compute_site_info')
    google_maps_link = fields.Char(string='Ver en Mapa', compute='_compute_site_info')
    contact_ids = fields.Many2many('res.partner', compute='_compute_contacts', string='Contactos de Emergencia')
    notes = fields.Text(string='Notas del Operador', placeholder='REGISTRE AQUÍ CADA PASO...')
    recent_signal_ids = fields.Many2many('sentinela.alarm.signal', compute='_compute_recent_signals', string='Señales Recientes')

    @api.depends('alarm_event_id', 'service_address_id')
    def _compute_site_info(self):
        for rec in self:
            addr = rec.service_address_id or rec.partner_id
            if addr:
                rec.address_display = f"{addr.street or ''}, {addr.street2 or ''}, {addr.city or ''}, {addr.state_id.name if addr.state_id else ''} CP {addr.zip or ''}"
                rec.site_phone = addr.phone or addr.mobile or "Sin teléfono"
                if rec.alarm_event_id.latitude and rec.alarm_event_id.longitude:
                    rec.google_maps_link = f"https://www.google.com/maps/search/?api=1&query={rec.alarm_event_id.latitude},{rec.alarm_event_id.longitude}"
                else:
                    rec.google_maps_link = False
            else:
                rec.address_display, rec.site_phone, rec.google_maps_link = "Sin dirección", "Sin teléfono", False

    @api.depends('alarm_event_id')
    def _compute_contacts(self):
        for rec in self:
            rec.contact_ids = self.env['res.partner'].search([('parent_id', '=', rec.partner_id.id), ('type', '=', 'contact')]) if rec.partner_id else False

    @api.depends('alarm_event_id')
    def _compute_recent_signals(self):
        for rec in self:
            rec.recent_signal_ids = self.env['sentinela.alarm.signal'].search([('device_id', '=', rec.alarm_event_id.device_id.id)], limit=5, order='create_date desc') if rec.alarm_event_id else False

    def _log_activity(self, message):
        now = fields.Datetime.now()
        # Mensaje con hora local
        full_msg = f"🔔 <b>ACTIVIDAD CENTRAL:</b> {message}<br/>🕒 Hora: {fields.Datetime.to_string(fields.Datetime.context_timestamp(self, now))}"
        self.alarm_event_id.message_post(body=full_msg)

    def action_open_maps(self):
        self.ensure_one()
        if self.google_maps_link:
            return {'type': 'ir.actions.act_url', 'url': self.google_maps_link, 'target': 'new'}
        return False

    def action_dispatch_patrol(self):
        self.ensure_one()
        fsm_order = self.env['sentinela.fsm.order'].create({
            'name': f"PATRULLA: {self.account_number}",
            'partner_id': self.partner_id.id,
            'service_address_id': self.service_address_id.id,
            'priority': '3',
            'service_type': 'patrol',
            'description': f"ATENCIÓN URGENTE. Notas: {self.notes or ''}",
            'alarm_event_id': self.alarm_event_id.id,
            'scheduled_date': fields.Datetime.now()
        })
        self._log_activity(f"🚓 <b>Patrulla Despachada:</b> Orden {fsm_order.name}. Notas: {self.notes or 'N/A'}")
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Patrulla Enviada', 'type': 'danger'}}

    def action_pause_event(self):
        self.ensure_one()
        self.alarm_event_id.write({'status': 'paused'})
        self._log_activity(f"⏸️ <b>Evento en Pausa:</b> El operador puso el evento en espera. Notas: {self.notes or 'N/A'}")
        return {'type': 'ir.actions.act_window_close'}

    def action_close_event(self):
        self.ensure_one()
        resolution = self.notes or "Evento finalizado sin notas adicionales."
        self.alarm_event_id.write({'status': 'resolved', 'end_date': fields.Datetime.now(), 'resolution_notes': resolution})
        self._log_activity(f"✅ <b>Evento Finalizado:</b> {resolution}")
        return {'type': 'ir.actions.act_window_close'}

    def action_create_technical_ticket(self):
        self.ensure_one()
        fsm_order = self.env['sentinela.fsm.order'].create({
            'name': f"FALLA TECNICA: {self.account_number}",
            'partner_id': self.partner_id.id,
            'service_type': 'repair',
            'alarm_event_id': self.alarm_event_id.id
        })
        self._log_activity(f"🔧 <b>Ticket Técnico Creado:</b> {fsm_order.name}. Notas: {self.notes or 'N/A'}")
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Ticket Creado', 'type': 'warning'}}

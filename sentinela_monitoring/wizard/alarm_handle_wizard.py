from odoo import models, fields, api, _
from datetime import datetime

class AlarmHandleWizard(models.TransientModel):
    _name = 'sentinela.alarm.handle.wizard'
    _description = 'Centro de Control'

    alarm_event_id = fields.Many2one('sentinela.alarm.event', string='Evento', readonly=True)
    partner_id = fields.Many2one('res.partner', related='alarm_event_id.partner_id', string='Cliente')
    account_number = fields.Char(related='alarm_event_id.account_number', string='Cuenta')
    
    # Campos dinámicos filtrados
    address_display = fields.Char(string='Dirección', compute='_compute_site_info')
    site_phone = fields.Char(string='Teléfono Sitio', compute='_compute_site_info')
    google_maps_link = fields.Char(string='Mapa')
    contact_ids = fields.Many2many('sentinela.monitoring.contact', compute='_compute_contacts', string='Contactos a Llamar')
    recent_signal_ids = fields.Many2many('sentinela.alarm.signal', compute='_compute_signals', string='Señales')
    
    notes = fields.Text(string='Notas del Operador', placeholder='REGISTRE PASOS...')
    extra_service_authorized = fields.Boolean(related='alarm_event_id.extra_service_authorized')
    patrol_included = fields.Boolean(default=False)

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

    def action_request_patrol_from_wizard(self):
        self.ensure_one()
        return self.alarm_event_id.action_request_service_authorization('patrol')

    def action_dispatch_patrol(self): return True
    def action_create_technical_ticket(self): return True
    def action_open_maps(self): return True

    def action_close_event(self):
        self.ensure_one()
        res = self.notes or "Cerrado"
        self.alarm_event_id.with_context(mail_notrack=True).write({'status': 'resolved', 'end_date': datetime.now(), 'resolution_notes': res})
        return {'type': 'ir.actions.act_window_close'}

    def action_pause_event(self):
        self.ensure_one()
        self.alarm_event_id.with_context(mail_notrack=True).write({'status': 'paused'})
        return {'type': 'ir.actions.act_window_close'}

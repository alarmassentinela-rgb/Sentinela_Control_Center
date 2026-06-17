from odoo import models, fields, api

class AlarmCodeTemplate(models.Model):
    _name = 'sentinela.alarm.code.template'
    _description = 'Plantilla Maestra de Códigos de Alarma'

    name = fields.Char(string='Nombre de la Plantilla', required=True, help="Ej. Plantilla Residencial Estándar")
    description = fields.Text(string='Descripción')

    line_ids = fields.One2many('sentinela.alarm.code.template.line', 'template_id', string='Configuración de Códigos')
    line_count = fields.Integer(string='Códigos', compute='_compute_line_count')
    active = fields.Boolean(default=True)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def action_load_all_codes(self):
        """Puebla la plantilla con TODOS los códigos del catálogo que aún no
        estén en ella, tomando prioridad y flags de notificación del código
        global. Idempotente: no duplica ni pisa las líneas ya personalizadas."""
        self.ensure_one()
        return self._load_codes(self.env['sentinela.alarm.code'].sudo().search([]))

    def action_load_attention_codes(self):
        """Como action_load_all_codes pero solo los códigos que generan evento
        atendible (requires_attention=True): alarmas y fallas."""
        self.ensure_one()
        codes = self.env['sentinela.alarm.code'].sudo().search([('requires_attention', '=', True)])
        return self._load_codes(codes)

    def _load_codes(self, codes):
        existing = set(self.line_ids.mapped('alarm_code_id').ids)
        vals = []
        for c in codes:
            if c.id in existing:
                continue
            vals.append((0, 0, {
                'alarm_code_id': c.id,
                'priority_id': c.priority_id.id if c.priority_id else False,
                'notify_email': c.notify_email,
                'notify_telegram': c.notify_telegram,
                'notify_whatsapp': c.notify_whatsapp,
            }))
        if vals:
            self.write({'line_ids': vals})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Plantilla actualizada',
                'message': f'Se añadieron {len(vals)} código(s); la plantilla tiene {len(self.line_ids)} en total.',
                'type': 'success' if vals else 'warning',
                'sticky': False,
            },
        }


class AlarmCodeTemplateLine(models.Model):
    _name = 'sentinela.alarm.code.template.line'
    _description = 'Línea de Plantilla de Código'
    _order = 'code_number asc'

    template_id = fields.Many2one('sentinela.alarm.code.template', string='Plantilla', ondelete='cascade')
    alarm_code_id = fields.Many2one('sentinela.alarm.code', string='Código de Alarma', required=True)
    code_number = fields.Char(related='alarm_code_id.code', string='Código', store=True)
    code_description = fields.Char(related='alarm_code_id.name', string='Descripción')
    event_category = fields.Selection(related='alarm_code_id.event_category', string='Categoría')

    priority_id = fields.Many2one('sentinela.alarm.priority', string='Prioridad')
    notify_email = fields.Boolean(string='Notificar Email', default=False)
    notify_telegram = fields.Boolean(string='Notificar Telegram', default=False)
    notify_whatsapp = fields.Boolean(string='Notificar WhatsApp', default=False)

    notes = fields.Char(string='Notas de Reacción')

from odoo import models, fields, api, _

class PatrolSelectionWizard(models.TransientModel):
    _name = 'sentinela.patrol.selection.wizard'
    _description = 'Selector de Contactos para Patrullaje'

    alarm_event_id = fields.Many2one('sentinela.alarm.event', string='Evento de Alarma', required=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', related='alarm_event_id.partner_id')
    
    line_ids = fields.One2many('sentinela.patrol.selection.line', 'wizard_id', string='Contactos con Telegram')

    @api.model
    def default_get(self, fields):
        res = super(PatrolSelectionWizard, self).default_get(fields)
        event_id = self.env.context.get('default_alarm_event_id')
        if event_id:
            event = self.env['sentinela.alarm.event'].browse(event_id)
            
            # BLINDAJE: Si la cuenta no está activa, no permitir abrir el wizard
            if not event.subscription_id or event.subscription_id.technical_state != 'active':
                raise models.ValidationError("⚠️ No se puede solicitar autorización para una cuenta que no tiene un servicio de monitoreo ACTIVO.")

            partner = event.partner_id
            if not partner:
                raise models.ValidationError("⚠️ Este evento no tiene un cliente vinculado.")

            lines = []
            
            # 1. Agregar al contacto principal si tiene Telegram
            if partner.telegram_chat_id:
                lines.append((0, 0, {
                    'partner_id': partner.id,
                    'name': partner.name,
                    'telegram_id': partner.telegram_chat_id,
                    'role': 'Titular',
                    'selected': True
                }))
            
            # 2. Agregar contactos hijos (gerentes, etc) que tengan Telegram
            for child in partner.child_ids:
                if child.telegram_chat_id:
                    lines.append((0, 0, {
                        'partner_id': child.id,
                        'name': child.name,
                        'telegram_id': child.telegram_chat_id,
                        'role': child.function or 'Contacto',
                        'selected': False
                    }))
            
            res['line_ids'] = lines
        return res

    def action_send_requests(self):
        selected_lines = self.line_ids.filtered(lambda l: l.selected)
        if not selected_lines:
            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Aviso', 'message': 'Seleccione al menos un contacto.', 'type': 'warning'}}
        
        # Llamar al método de envío real por cada seleccionado
        for line in selected_lines:
            self.alarm_event_id.with_context(target_chat_id=line.telegram_id).request_patrol_v2()
            
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Éxito', 'message': 'Solicitudes de cobro enviadas.', 'type': 'success'}}

class PatrolSelectionLine(models.TransientModel):
    _name = 'sentinela.patrol.selection.line'
    _description = 'Línea de Selección de Contacto'

    wizard_id = fields.Many2one('sentinela.patrol.selection.wizard')
    partner_id = fields.Many2one('res.partner', string='Contacto')
    name = fields.Char(string='Nombre')
    telegram_id = fields.Char(string='ID Telegram')
    role = fields.Char(string='Puesto/Rol')
    selected = fields.Boolean(string='Enviar', default=False)

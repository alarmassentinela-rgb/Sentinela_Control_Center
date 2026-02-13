from odoo import models, fields, api, _

class SubscriptionCloseWizard(models.TransientModel):
    _name = 'sentinela.subscription.close.wizard'
    _description = 'Asistente para Suspensión o Cancelación'

    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción', required=True)
    action_type = fields.Selection([
        ('suspend', 'Suspender Servicio'),
        ('cancel', 'Cancelar Contrato')
    ], string='Acción', required=True)

    reason_type = fields.Selection([
        ('payment', 'Falta de Pago'),
        ('technical', 'Falla Técnica'),
        ('customer_request', 'Solicitud del Cliente'),
        ('bad_service', 'Mal Servicio'),
        ('moving', 'Cambio de Domicilio (No renovado)'),
        ('other', 'Otro (Especificar)')
    ], string='Motivo Principal', required=True, default='payment')

    notes = fields.Text(string='Comentarios / Detalles', required=True)

    def action_confirm(self):
        self.ensure_one()
        # Construir el mensaje para el Chatter
        log_message = f"<b>ACCIÓN: {self.action_type.upper()}</b><br/>"
        log_message += f"<b>Motivo:</b> {dict(self._fields['reason_type'].selection).get(self.reason_type)}<br/>"
        log_message += f"<b>Detalles:</b> {self.notes}"

        # Registrar en el historial
        self.subscription_id.message_post(body=log_message)

        # Ejecutar la acción técnica según corresponda
        if self.action_type == 'suspend':
            return self.subscription_id.action_suspend()
        elif self.action_type == 'cancel':
            return self.subscription_id.action_cancel()

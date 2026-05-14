from odoo import models, fields, api

class SentinelaSubscriptionGenerateConfirm(models.TransientModel):
    _name = 'sentinela.subscription.generate.confirm'
    _description = 'Confirmar Regeneración de Contrato'

    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción')
    message = fields.Text(default="Ya existe un contrato vigente para esta suscripción. ¿Deseas generar uno nuevo? (El contrato anterior se conservará en el historial).")

    def action_confirm(self):
        return self.subscription_id.with_context(bypass_confirm=True).action_generate_contract()

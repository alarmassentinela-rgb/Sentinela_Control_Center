from datetime import timedelta
from odoo import models, fields, api

class SentinelaSubscriptionExtensionWizard(models.TransientModel):
    _name = 'sentinela.subscription.extension.wizard'
    _description = 'Otorgar Prórroga Temporal'

    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción', required=True)
    extension_date = fields.Date(string='Fecha de Prórroga', required=True, help="Fecha hasta la cual el cliente podrá navegar.")
    reason = fields.Text(string='Motivo / Nota', required=True, help="Explique por qué se otorga la prórroga (ej. Promesa de pago).")

    @api.model
    def default_get(self, fields):
        res = super(SentinelaSubscriptionExtensionWizard, self).default_get(fields)
        if self.env.context.get('active_model') == 'sentinela.subscription' and self.env.context.get('active_id'):
            res['subscription_id'] = self.env.context.get('active_id')
        # Por defecto dar 3 dias
        res['extension_date'] = fields.Date.today() + timedelta(days=3)
        return res

    def action_apply_extension(self):
        self.ensure_one()
        self.subscription_id.apply_date_extension(self.extension_date, self.reason)
        return {'type': 'ir.actions.act_window_close'}

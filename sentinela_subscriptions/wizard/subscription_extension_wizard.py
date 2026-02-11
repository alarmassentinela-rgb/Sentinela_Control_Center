from odoo import models, fields, api

class SentinelaSubscriptionExtensionWizard(models.TransientModel):
    _name = 'sentinela.subscription.extension.wizard'
    _description = 'Otorgar Prórroga Temporal'

    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción', required=True)
    days = fields.Integer(string='Días de Prórroga', default=3, required=True)
    reason = fields.Text(string='Motivo / Nota', required=True, help="Explique por qué se otorga la prórroga (ej. Promesa de pago para el viernes).")

    @api.model
    def default_get(self, fields):
        res = super(SentinelaSubscriptionExtensionWizard, self).default_get(fields)
        if self.env.context.get('active_model') == 'sentinela.subscription' and self.env.context.get('active_id'):
            res['subscription_id'] = self.env.context.get('active_id')
        return res

    def action_apply_extension(self):
        self.ensure_one()
        self.subscription_id.apply_extension(self.days, self.reason)
        return {'type': 'ir.actions.act_window_close'}

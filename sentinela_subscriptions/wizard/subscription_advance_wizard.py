from dateutil.relativedelta import relativedelta
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SentinelaSubscriptionAdvanceWizard(models.TransientModel):
    _name = 'sentinela.subscription.advance.wizard'
    _description = 'Cobro de Meses por Adelantado'

    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción', required=True)
    months = fields.Integer(string='Meses a Adelantar', required=True, default=3)
    price_unit = fields.Float(related='subscription_id.price_unit', string='Tarifa Mensual', readonly=True)
    period_start = fields.Date(related='subscription_id.next_billing_date', string='Inicio del Periodo', readonly=True)
    period_end = fields.Date(string='Fin del Periodo', compute='_compute_period')
    estimated_total = fields.Float(string='Total estimado (Sin IVA)', compute='_compute_period')

    @api.depends('months', 'subscription_id.price_unit', 'subscription_id.next_billing_date')
    def _compute_period(self):
        for w in self:
            start = w.subscription_id.next_billing_date or fields.Date.today()
            m = w.months or 0
            w.period_end = (start + relativedelta(months=m) - timedelta(days=1)) if m > 0 else start
            w.estimated_total = m * (w.subscription_id.price_unit or 0)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'sentinela.subscription' and self.env.context.get('active_id'):
            res['subscription_id'] = self.env.context.get('active_id')
        return res

    def action_create_invoice(self):
        """ Crea la factura BORRADOR de N meses, ligada a la suscripción y marcada como cobro
        adelantado. No la publica: el usuario la revisa y timbra. Al publicarla, el override de
        account.move.action_post empuja next_billing_date N meses. """
        self.ensure_one()
        if self.months < 1:
            raise UserError(_("Indica al menos 1 mes a adelantar."))
        sub = self.subscription_id
        if not sub.product_id:
            raise UserError(_("La suscripción no tiene plan (producto) definido."))
        period_start = sub.next_billing_date or fields.Date.today()
        period_end = period_start + relativedelta(months=self.months) - timedelta(days=1)
        desc = _("Pago adelantado %s mes(es) - %s - Contrato: %s - Periodo: %s al %s") % (
            self.months, sub.product_id.name, sub.name, period_start, period_end)
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': sub.partner_id.id,
            'invoice_date': fields.Date.today(),
            'fiscal_position_id': sub.partner_id.property_account_position_id.id or False,
            'invoice_payment_term_id': sub.payment_term_id.id or False,
            'subscription_id': sub.id,
            'is_advance_payment': True,
            'invoice_origin': _("Cobro adelantado: %s") % sub.name,
            'invoice_line_ids': [(0, 0, {
                'product_id': sub.product_id.id,
                'name': desc,
                'quantity': self.months,
                'price_unit': sub.price_unit,
            })],
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura de Cobro Adelantado'),
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }

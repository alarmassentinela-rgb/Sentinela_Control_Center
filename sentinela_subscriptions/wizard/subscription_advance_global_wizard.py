from dateutil.relativedelta import relativedelta
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SubscriptionAdvanceGlobalWizard(models.TransientModel):
    _name = 'sentinela.subscription.advance.global.wizard'
    _description = 'Cobro Adelantado Global del Cliente'

    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    n_ciclos = fields.Integer(string='Ciclos a adelantar', required=True, default=1)
    line_ids = fields.One2many(
        'sentinela.subscription.advance.global.line', 'wizard_id',
        string='Detalle por suscripción', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    estimated_total = fields.Monetary(string='Total estimado (sin IVA)', compute='_compute_total', currency_field='currency_id')
    sub_count = fields.Integer(string='Suscripciones', compute='_compute_total')
    mixed_intervals = fields.Boolean(compute='_compute_total')

    def _eligible_subs(self, partner):
        """ Todas las suscripciones activas facturables del cliente (excluye cortesía).
        Es SIEMPRE el conjunto completo: el adelanto global abarca al cliente entero (decisión #A). """
        return self.env['sentinela.subscription'].search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'active'),
            ('billing_mode', '!=', 'courtesy'),
        ])

    def _build_preview(self, partner, n):
        """ Comandos (0,0,{...}) para line_ids: una fila por suscripción con la fecha de cobro
        ANTES y DESPUÉS del adelanto. Cantidad/monto desde la fuente única _billing_line_qty. """
        n = max(1, int(n or 1))
        cmds = [(5, 0, 0)]
        for sub in self._eligible_subs(partner):
            interval = int(sub.recurring_interval or 1)
            months = n * interval
            cur = sub.next_billing_date
            proj = (cur + relativedelta(months=months)) if cur else False
            cmds.append((0, 0, {
                'subscription_id': sub.id,
                'plan_name': sub.product_id.name or '',
                'service_type': sub.service_type,
                'interval': interval,
                'ciclos': n,
                'months': months,
                'current_date': cur,
                'projected_date': proj,
                'amount': sub.price_unit * sub._billing_line_qty(n),
            }))
        return cmds

    @api.depends('line_ids', 'line_ids.amount', 'line_ids.interval')
    def _compute_total(self):
        for w in self:
            w.estimated_total = sum(w.line_ids.mapped('amount'))
            w.sub_count = len(w.line_ids)
            w.mixed_intervals = len(set(w.line_ids.mapped('interval'))) > 1

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        partner_id = res.get('partner_id') or self.env.context.get('default_partner_id')
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            res['line_ids'] = self._build_preview(partner, res.get('n_ciclos') or 1)
        return res

    @api.onchange('partner_id', 'n_ciclos')
    def _onchange_recompute_preview(self):
        if self.partner_id:
            self.line_ids = self._build_preview(self.partner_id, self.n_ciclos)

    def action_create_invoice(self):
        """ Crea la factura BORRADOR del adelanto global (todas las subs del cliente), marcada con
        advance_periods=n_ciclos. Al publicarla, _advance_on_post empuja el ciclo de cada sub
        n_ciclos × su intervalo. No la publica: el operador la revisa/timbra. """
        self.ensure_one()
        if self.n_ciclos < 1:
            raise UserError(_("Indica al menos 1 ciclo a adelantar."))
        partner = self.partner_id
        subs = self._eligible_subs(partner)
        if not subs:
            raise UserError(_("El cliente %s no tiene suscripciones activas facturables.") % partner.display_name)

        # 🚫 Bloqueo anti-concurrencia (decisión #5): nada de dos adelantos sobre las mismas subs.
        self.env['account.move']._check_no_concurrent_global_advance(partner, subs)

        first = subs[0]
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'fiscal_position_id': partner.property_account_position_id.id or False,
            'invoice_payment_term_id': first.payment_term_id.id or False,
            'is_advance_payment': True,
            'advance_periods': self.n_ciclos,
            'subscription_ids': [(6, 0, subs.ids)],
            'subscription_id': first.id if len(subs) == 1 else False,
            'invoice_origin': _("Cobro adelantado global: %s (%s ciclo(s))") % (partner.name, self.n_ciclos),
            'invoice_line_ids': subs._build_group_lines(subs, self.n_ciclos),
            'cfdi_status': 'pending' if partner.requiere_factura else 'draft',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura de Cobro Adelantado Global'),
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }


class SubscriptionAdvanceGlobalLine(models.TransientModel):
    _name = 'sentinela.subscription.advance.global.line'
    _description = 'Preview de Cobro Adelantado Global (por suscripción)'
    _order = 'projected_date asc'

    wizard_id = fields.Many2one('sentinela.subscription.advance.global.wizard', ondelete='cascade')
    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción', readonly=True)
    plan_name = fields.Char(string='Plan', readonly=True)
    service_type = fields.Char(string='Tipo', readonly=True)
    interval = fields.Integer(string='Intervalo (meses)', readonly=True)
    ciclos = fields.Integer(string='Ciclos', readonly=True)
    months = fields.Integer(string='Meses adelantados', readonly=True)
    current_date = fields.Date(string='Próx. cobro ACTUAL', readonly=True)
    projected_date = fields.Date(string='Próx. cobro TRAS adelanto', readonly=True)
    currency_id = fields.Many2one(related='wizard_id.currency_id')
    amount = fields.Monetary(string='Importe (sin IVA)', readonly=True, currency_field='currency_id')

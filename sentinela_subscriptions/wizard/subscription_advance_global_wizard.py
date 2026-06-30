from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SubscriptionAdvanceGlobalWizard(models.TransientModel):
    _name = 'sentinela.subscription.advance.global.wizard'
    _description = 'Cobro Adelantado Global del Cliente'

    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    n_ciclos = fields.Integer(string='Ciclos a adelantar', required=True, default=1)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    estimated_total = fields.Monetary(string='Total estimado (sin IVA)', compute='_compute_preview', currency_field='currency_id')
    sub_count = fields.Integer(string='Suscripciones', compute='_compute_preview')
    mixed_intervals = fields.Boolean(compute='_compute_preview')
    preview_html = fields.Html(string='Detalle por suscripción', compute='_compute_preview', sanitize=False)

    def _eligible_subs(self, partner):
        """ Suscripciones del cliente elegibles para el adelanto: estado `active` O `suspension`
        (las "vivas" — la suspendida por mora también puede prepagar y se reactiva al pagar),
        excluyendo cortesía. Aplica tanto a clientes de factura como de REMISIÓN (el tipo de
        documento lo decide `requiere_factura` al crear el move, no la elegibilidad). Es SIEMPRE
        el conjunto completo: el adelanto global abarca al cliente entero (decisión #A). """
        if not partner:
            return self.env['sentinela.subscription']
        return self.env['sentinela.subscription'].search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ('active', 'suspension')),
            ('billing_mode', '!=', 'courtesy'),
        ])

    @api.depends('partner_id', 'n_ciclos')
    def _compute_preview(self):
        """ Preview server-side (tabla HTML): por cada suscripción del cliente, fecha de cobro
        ANTES y DESPUÉS del adelanto + importe. Sin depender de la mecánica x2many del cliente web.
        Cantidad/monto desde la fuente única _billing_line_qty. """
        for w in self:
            subs = w._eligible_subs(w.partner_id)
            n = max(1, int(w.n_ciclos or 1))
            total = 0.0
            intervals = set()
            rows = []
            for sub in subs:
                interval = int(sub.recurring_interval or 1)
                intervals.add(interval)
                months = n * interval
                cur = sub.next_billing_date
                proj = (cur + relativedelta(months=months)) if cur else False
                amount = sub.price_unit * sub._billing_line_qty(n)
                total += amount
                cur_s = cur.strftime('%d/%m/%Y') if cur else '—'
                proj_s = proj.strftime('%d/%m/%Y') if proj else '—'
                rows.append(
                    f"<tr><td>{sub.name}</td><td>{sub.product_id.name or ''}</td>"
                    f"<td class='text-end'>{interval}</td><td class='text-end'>{months}</td>"
                    f"<td>{cur_s}</td><td class='text-end'><b>{proj_s}</b></td>"
                    f"<td class='text-end'>${amount:,.2f}</td></tr>")
            if rows:
                w.preview_html = (
                    "<table class='table table-sm table-striped o_list_table'>"
                    "<thead><tr>"
                    "<th>Suscripción</th><th>Plan</th>"
                    "<th class='text-end'>Interv. (meses)</th><th class='text-end'>Meses</th>"
                    "<th>Próx. cobro ACTUAL</th><th class='text-end'>Próx. cobro TRAS adelanto</th>"
                    "<th class='text-end'>Importe (sin IVA)</th>"
                    "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>")
            elif w.partner_id:
                w.preview_html = "<div class='alert alert-warning mb-0'>Este cliente no tiene suscripciones activas o suspendidas para adelantar (las de cortesía no aplican).</div>"
            else:
                w.preview_html = "<div class='text-muted'>Selecciona un cliente.</div>"
            w.estimated_total = total
            w.sub_count = len(subs)
            w.mixed_intervals = len(intervals) > 1

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
            raise UserError(_("El cliente %s no tiene suscripciones activas o suspendidas para adelantar.") % partner.display_name)

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

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

    # --- Lógica de Penalización por Plazo Forzoso (v18.0.1.3.3) ---
    is_within_plazo = fields.Boolean(compute='_compute_plazo_info', string='Dentro del plazo forzoso')
    commitment_end_date = fields.Date(related='subscription_id.commitment_end_date', readonly=True)
    penalty_suggested = fields.Monetary(
        related='subscription_id.early_termination_fee',
        currency_field='currency_id',
        readonly=True,
        string='Penalización Configurada',
    )
    currency_id = fields.Many2one('res.currency', related='subscription_id.currency_id', readonly=True)
    apply_penalty = fields.Boolean(string='Facturar penalización al cancelar', default=True)
    penalty_amount_to_charge = fields.Monetary(
        string='Monto a Facturar',
        currency_field='currency_id',
        help='Puedes ajustar el monto antes de facturar (ej: descuento por VIP).',
    )

    @api.depends('subscription_id', 'subscription_id.commitment_end_date', 'subscription_id.is_forced_contract')
    def _compute_plazo_info(self):
        today = fields.Date.today()
        for w in self:
            sub = w.subscription_id
            w.is_within_plazo = (
                sub.is_forced_contract
                and sub.commitment_end_date
                and sub.commitment_end_date > today
            )

    @api.onchange('subscription_id', 'apply_penalty')
    def _onchange_apply_penalty(self):
        for w in self:
            if w.apply_penalty and w.penalty_suggested:
                w.penalty_amount_to_charge = w.penalty_suggested

    def action_confirm(self):
        self.ensure_one()
        log_message = f"<b>ACCIÓN: {self.action_type.upper()}</b><br/>"
        log_message += f"<b>Motivo:</b> {dict(self._fields['reason_type'].selection).get(self.reason_type)}<br/>"
        log_message += f"<b>Detalles:</b> {self.notes}"

        self.subscription_id.message_post(body=log_message)

        # Facturar penalización si aplica
        if (self.action_type == 'cancel'
                and self.is_within_plazo
                and self.apply_penalty
                and self.penalty_amount_to_charge > 0):
            self._create_penalty_invoice()

        if self.action_type == 'suspend':
            return self.subscription_id.action_suspend()
        elif self.action_type == 'cancel':
            return self.subscription_id.action_cancel()

    def _create_penalty_invoice(self):
        """Genera factura de penalización por cancelación dentro de plazo forzoso."""
        self.ensure_one()
        sub = self.subscription_id
        product = self.env['product.product'].search(
            [('default_code', '=', 'PENALIZACION_RESCISION')], limit=1
        )
        if not product:
            product = self.env['product.product'].create({
                'name': 'Penalización por Cancelación Anticipada',
                'default_code': 'PENALIZACION_RESCISION',
                'type': 'service',
                'list_price': 0.0,
                'taxes_id': False,
            })
        invoice_vals = {
            'partner_id': sub.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_origin': f'Penalización por cancelación contrato {sub.name}',
            'subscription_id': sub.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'name': (f'Penalización por cancelación anticipada del contrato {sub.name}.\n'
                         f'Plazo forzoso vigente hasta {sub.commitment_end_date}.'),
                'quantity': 1,
                'price_unit': self.penalty_amount_to_charge,
            })],
        }
        invoice = self.env['account.move'].create(invoice_vals)
        sub.message_post(
            body=(f"💰 <b>Factura de Penalización Generada:</b> "
                  f"{invoice.name or 'borrador'} por "
                  f"${self.penalty_amount_to_charge:,.2f} {self.currency_id.name or 'MXN'}.")
        )
        return invoice

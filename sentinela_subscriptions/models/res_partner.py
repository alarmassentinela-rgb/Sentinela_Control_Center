from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_grouping_method = fields.Selection([
        ('individual', 'Una factura por servicio detallado'),
        ('by_branch', 'Agrupar por sucursal'),
        ('global', 'Una factura global todo junto')
    ], string='Preferencia de Facturación', default='individual', 
    help="Define cómo prefiere el cliente recibir sus facturas de suscripción.")

    # --- Condiciones de Venta para Facturación Automática ---
    invoice_payment_condition = fields.Selection([
        ('contado', 'Contado'),
        ('credito', 'Crédito'),
        ('otro', 'Otro')
    ], string='Condición de Pago', default='contado')
    invoice_payment_condition_text = fields.Char(string='Especifique Condición')

    invoice_payment_form = fields.Selection([
        ('01', '01 - Efectivo'),
        ('02', '02 - Cheque nominativo'),
        ('03', '03 - Transferencia electrónica de fondos'),
        ('04', '04 - Tarjeta de crédito'),
        ('05', '05 - Monedero electrónico'),
        ('06', '06 - Dinero electrónico'),
        ('08', '08 - Vales de despensa'),
        ('12', '12 - Dación en pago'),
        ('13', '13 - Pago por subrogación'),
        ('14', '14 - Pago por consignación'),
        ('15', '15 - Condonación'),
        ('17', '17 - Compensación'),
        ('23', '23 - Novación'),
        ('24', '24 - Confusión'),
        ('25', '25 - Remisión de deuda'),
        ('26', '26 - Prescripción o caducidad'),
        ('27', '27 - A satisfacción del acreedor'),
        ('28', '28 - Tarjeta de débito'),
        ('29', '29 - Tarjeta de servicios'),
        ('30', '30 - Aplicación de anticipos'),
        ('31', '31 - Intermediario pagos'),
        ('99', '99 - Por definir')
    ], string='Forma de Pago', default='99')

    invoice_bank_account = fields.Char(string='Número de Cuenta (4 dígitos)', size=4)
    
    invoice_payment_method = fields.Selection([
        ('PUE', 'PUE - Pago en una sola exhibición'),
        ('PPD', 'PPD - Pago en parcialidades o diferido')
    ], string='Método de Pago', default='PUE')

    invoice_zip = fields.Char(string='Lugar de Expedición', default='87350')

    # --- Condiciones CFDI ---
    invoice_cfdi_usage = fields.Selection([
        ('G01', 'Adquisición de mercancías'),
        ('G03', 'Gastos en general'),
        ('I01', 'Construcciones'),
        ('S01', 'Sin efectos fiscales'),
        ('CP01', 'Pagos'),
        ('P01', 'Por definir (Obsoleto CFDI 4.0)')
    ], string='Uso CFDI', default='G03')

    subscription_count = fields.Integer(compute='_compute_subscription_count', string='# Subscriptions')
    
    def _compute_subscription_count(self):
        for partner in self:
            partner.subscription_count = self.env['sentinela.subscription'].search_count([('partner_id', '=', partner.id)])

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subscriptions',
            'view_mode': 'list,form',
            'res_model': 'sentinela.subscription',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    @api.depends('name', 'parent_id.name')
    def _compute_display_name(self):
        if self._context.get('show_only_name'):
            for partner in self:
                partner.display_name = partner.name
        else:
            super()._compute_display_name()

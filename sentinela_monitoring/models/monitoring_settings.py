from odoo import models, fields, api

class MonitoringSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    monitoring_next_account_number = fields.Integer(
        string='Siguiente Cuenta de Monitoreo',
        config_parameter='sentinela_monitoring.next_account_number',
        help="El número que se asignará a la próxima instalación de alarma nueva."
    )

    traccar_url = fields.Char(
        string='URL de Radar Senticar (Traccar)',
        config_parameter='sentinela.traccar_url',
        default='https://senticar.com',
        help="La URL que se incrustará en el Radar del Dashboard."
    )

    # F2.6 — Cobranza al atender
    patrol_service_product_id = fields.Many2one(
        'product.product',
        string='Producto Servicio de Patrulla',
        config_parameter='sentinela_monitoring.patrol_service_product_id',
        help='Producto / servicio que se factura cuando el operador despacha '
             'una patrulla autorizada. Se usa para crear la sale.order automática.',
    )

    @api.model
    def get_values(self):
        res = super(MonitoringSettings, self).get_values()
        seq = self.env.ref('sentinela_monitoring.seq_sentinela_monitoring_account', raise_if_not_found=False)
        if seq:
            res.update(
                monitoring_next_account_number=seq.number_next_actual,
            )
        return res

    def set_values(self):
        super(MonitoringSettings, self).set_values()
        seq = self.env.ref('sentinela_monitoring.seq_sentinela_monitoring_account', raise_if_not_found=False)
        if seq and self.monitoring_next_account_number:
            seq.write({'number_next': self.monitoring_next_account_number})

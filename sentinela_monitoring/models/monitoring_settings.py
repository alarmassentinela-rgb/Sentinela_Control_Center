from odoo import models, fields, api

class MonitoringSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    monitoring_next_account_number = fields.Integer(
        string='Siguiente Cuenta de Monitoreo',
        config_parameter='sentinela_monitoring.next_account_number',
        help="El número que se asignará a la próxima instalación de alarma nueva."
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

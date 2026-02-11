from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class SentinelaSubscription(models.Model):
    _inherit = 'sentinela.subscription'

    monitoring_device_ids = fields.One2many('sentinela.monitoring.device', 'subscription_id', string='Dispositivos de Monitoreo')

    def action_activate(self):
        res = super(SentinelaSubscription, self).action_activate()
        for device in self.monitoring_device_ids:
            device.action_activate_device()
            _logger.info(f"MONITORING: Activated device {device.name} for subscription {self.name}")
        return res

    def action_suspend(self):
        res = super(SentinelaSubscription, self).action_suspend()
        for device in self.monitoring_device_ids:
            device.action_deactivate_device()
            _logger.info(f"MONITORING: Suspended device {device.name} for subscription {self.name}")
        return res

    def action_cancel(self):
        res = super(SentinelaSubscription, self).action_cancel()
        for device in self.monitoring_device_ids:
            device.action_deactivate_device()
            _logger.info(f"MONITORING: Cancelled device {device.name} for subscription {self.name}")
        return res

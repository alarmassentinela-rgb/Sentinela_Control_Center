from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class SentinelaSubscription(models.Model):
    _inherit = 'sentinela.subscription'

    monitoring_device_ids = fields.One2many('sentinela.monitoring.device', 'subscription_id', string='Dispositivos de Monitoreo')
    alarm_event_ids = fields.One2many('sentinela.alarm.event', 'subscription_id', string='Historial de Alarmas')
    monitoring_call_ids = fields.One2many('sentinela.monitoring.call', 'subscription_id', string='Historial de Llamadas')
    monitoring_device_count = fields.Integer(
        string='Núm. paneles', compute='_compute_monitoring_device_count')

    @api.depends('monitoring_device_ids')
    def _compute_monitoring_device_count(self):
        for rec in self:
            rec.monitoring_device_count = len(rec.monitoring_device_ids)

    def action_view_monitoring_devices(self):
        """Smart button: abre los paneles de monitoreo de esta suscripción de
        alarma. Si aún no hay, abre el alta precargando cliente + suscripción
        (el número de cuenta se sugiere como consecutivo de 4 dígitos)."""
        self.ensure_one()
        ctx = dict(self.env.context,
                   default_partner_id=self.partner_id.id,
                   default_subscription_id=self.id)
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Cuentas de Monitoreo'),
            'res_model': 'sentinela.monitoring.device',
            'context': ctx,
        }
        devices = self.monitoring_device_ids
        if len(devices) == 1:
            action.update(view_mode='form', res_id=devices.id)
        elif len(devices) > 1:
            action.update(view_mode='list,form', domain=[('id', 'in', devices.ids)])
        else:
            action.update(view_mode='form')
        return action

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

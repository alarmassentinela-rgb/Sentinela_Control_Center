from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_syscom_order = fields.Boolean(string='Es Orden Syscom', default=False)
    syscom_order_id = fields.Char(string='ID Orden Syscom', readonly=True)
    syscom_order_status = fields.Selection([
        ('Pendiente', 'Pendiente'),
        ('Enviado', 'Enviado'),
        ('Entregado', 'Entregado'),
        ('Cancelado', 'Cancelado')
    ], string='Estado Syscom', default='Pendiente')
    syscom_delivery_date = fields.Datetime(string='Fecha de Entrega Est.')
    syscom_shipment_ids = fields.One2many('sentinela.syscom.shipment', 'purchase_id', string='Envíos Syscom')

    def action_send_to_syscom(self):
        self.ensure_one()
        _logger.info(f"SENTINELA: Procesando envío de Orden {self.name}")
        self.write({'is_syscom_order': True, 'syscom_order_id': 'AUTO-PROCESANDO'})
        return True

    def action_sync_syscom_status(self):
        self.ensure_one()
        _logger.info(f"SENTINELA: Rastreo de Orden {self.syscom_order_id}")
        return True

class SyscomShipment(models.Model):
    _name = 'sentinela.syscom.shipment'
    _description = 'Guía de Rastreo Syscom'

    purchase_id = fields.Many2one('purchase.order', string='Orden de Compra')
    courier = fields.Char(string='Paquetería')
    tracking_number = fields.Char(string='Número de Guía')
    status = fields.Char(string='Estado Actual')
    tracking_url = fields.Char(string='URL Rastreo')

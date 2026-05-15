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
        """Pendiente de implementar v18.0.1.2.0: antes fingía éxito sin hacer nada."""
        self.ensure_one()
        raise UserError(
            "El envío automático de órdenes a Syscom aún no está implementado.\n\n"
            "Por ahora, captura la orden manualmente en el portal de Syscom y "
            "registra el ID en el campo 'ID Orden Syscom' para llevar la traza."
        )

    def action_sync_syscom_status(self):
        """Pendiente de implementar v18.0.1.2.0: antes fingía éxito sin hacer nada."""
        self.ensure_one()
        raise UserError(
            "El rastreo automático de órdenes Syscom aún no está implementado.\n\n"
            "Por ahora, consulta el estado y la guía directamente en el portal de Syscom y "
            "registra la información en la pestaña 'Envíos Syscom'."
        )

class SyscomShipment(models.Model):
    _name = 'sentinela.syscom.shipment'
    _description = 'Guía de Rastreo Syscom'

    purchase_id = fields.Many2one('purchase.order', string='Orden de Compra')
    courier = fields.Char(string='Paquetería')
    tracking_number = fields.Char(string='Número de Guía')
    status = fields.Char(string='Estado Actual')
    tracking_url = fields.Char(string='URL Rastreo')

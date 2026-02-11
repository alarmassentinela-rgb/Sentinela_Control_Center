from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_confirm(self):
        """ Extend confirmation to create FSM orders for specific service types """
        res = super(SaleOrder, self)._action_confirm()
        
        FsmOrder = self.env['sentinela.fsm.order']
        
        for order in self:
            # 1. Logic for Address Transfer
            if hasattr(order, 'target_transfer_address_id') and order.target_transfer_address_id:
                # We know this is a transfer because of the special field
                # The address update is already handled in sentinela_subscriptions, 
                # here we just create the technical task.
                FsmOrder.create({
                    'partner_id': order.partner_id.id,
                    'service_address_id': order.target_transfer_address_id.id,
                    'subscription_id': order.subscription_id.id if hasattr(order, 'subscription_id') else False,
                    'description': f"INSTALACIÓN POR TRASLADO: Mover equipo a nueva dirección pagada en orden {order.name}.<br/>Nueva Dirección: {order.target_transfer_address_id.contact_address}",
                    'priority': '1', # High priority
                })
                _logger.info(f"FSM: Created Transfer Order for {order.partner_id.name}")

            # 2. Logic for Reconnection
            elif order.origin and "Reactivación" in order.origin:
                # Based on the origin string we set in action_quote_reconnection
                FsmOrder.create({
                    'partner_id': order.partner_id.id,
                    'service_address_id': order.partner_shipping_id.id or order.partner_id.id,
                    'subscription_id': order.subscription_id.id if hasattr(order, 'subscription_id') else False,
                    'description': f"RECONEXIÓN TÉCNICA: Cliente pagó reconexión en orden {order.name}. Verificar señal y estado físico del CPE.",
                    'priority': '2', # Urgent
                })
                _logger.info(f"FSM: Created Reconnection Order for {order.partner_id.name}")

        return res

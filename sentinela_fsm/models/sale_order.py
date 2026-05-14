from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_confirm(self):
        """ Extend confirmation to create FSM orders for specific service types """
        res = super(SaleOrder, self)._action_confirm()
        
        FsmOrder = self.env['sentinela.fsm.order']
        Subscription = self.env['sentinela.subscription']
        
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
                    'service_type': 'transfer',
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
                    'service_type': 'repair',
                    'priority': '2', # Urgent
                })
                _logger.info(f"FSM: Created Reconnection Order for {order.partner_id.name}")

            # 3. AUTOMATION: Initial Installation for new Subscriptions
            # Find lines that are subscriptions and don't have a sub_id yet
            # (Note: subscription_id field is usually on the SO, but we check lines too if needed)
            sub_lines = order.order_line.filtered(lambda l: l.product_id.is_subscription)
            
            for line in sub_lines:
                # REVISIÓN DE RENOVACIÓN: No crear FSM si el contrato ya está activo (es una renovación)
                # Buscamos si ya existe una suscripción activa para este cliente y producto
                existing_active_sub = Subscription.search([
                    ('partner_id', '=', order.partner_id.id),
                    ('product_id', '=', line.product_id.id),
                    ('state', 'in', ['active', 'closed', 'suspended'])
                ], limit=1)
                
                if existing_active_sub:
                    _logger.info(f"FSM: Skipping auto-creation for renewal of {order.partner_id.name}")
                    continue

                # Avoid duplicates if this SO was already processed or partially processed
                # We check if there's already an FSM order or Sub linked to this SO for this product
                existing_sub = Subscription.search([
                    ('partner_id', '=', order.partner_id.id),
                    ('product_id', '=', line.product_id.id),
                    ('state', '=', 'draft'),
                    ('create_date', '>=', fields.Datetime.now() - relativedelta(minutes=5))
                ], limit=1)
                
                if not existing_sub:
                    # Create the Draft Subscription
                    new_sub = Subscription.create({
                        'partner_id': order.partner_id.id,
                        'service_address_id': order.partner_shipping_id.id or order.partner_id.id,
                        'product_id': line.product_id.id,
                        'price_unit': line.price_unit,
                        'service_type': line.product_id.service_type or 'alarm',
                        'recurring_interval': line.product_id.default_recurring_interval or '1',
                        'next_billing_date': fields.Date.today(), # ASIGNAR FECHA PARA EVITAR ERROR DE VALIDACIÓN
                        'state': 'draft',
                    })
                    
                    # Create the FSM Installation Order
                    FsmOrder.create({
                        'partner_id': order.partner_id.id,
                        'service_address_id': order.partner_shipping_id.id or order.partner_id.id,
                        'subscription_id': new_sub.id,
                        'service_type': 'install',
                        'description': f"INSTALACIÓN INICIAL: Servicio {line.product_id.name} vendido en orden {order.name}.<br/>Favor de realizar instalación física y capturar datos técnicos.",
                        'priority': '1',
                    })
                    _logger.info(f"FSM/SUB: Auto-created Installation flow for {order.partner_id.name}")

            # 4. AUTOMATION: One-time Service Orders (non-subscriptions)
            # Find lines that are SERVICES but NOT marked as subscription (those are handled above)
            service_lines = order.order_line.filtered(lambda l: l.product_id.type == 'service' and not l.product_id.is_subscription)
            
            for s_line in service_lines:
                # Check if we already created an FSM order for this SO/Product recently to avoid dupes
                # (Simple check by description/origin)
                existing_fsm = FsmOrder.search([
                    ('partner_id', '=', order.partner_id.id),
                    ('description', 'like', order.name),
                    ('create_date', '>=', fields.Datetime.now() - relativedelta(minutes=5))
                ], limit=1)
                
                if not existing_fsm:
                    FsmOrder.create({
                        'partner_id': order.partner_id.id,
                        'service_address_id': order.partner_shipping_id.id or order.partner_id.id,
                        'service_type': 'install' if 'Instalación' in s_line.product_id.name else 'repair',
                        'description': f"ORDEN DE SERVICIO TÉCNICO: {s_line.product_id.name} vendido en {order.name}.<br/>Realizar el trabajo solicitado y documentar.",
                        'priority': '0',
                    })
                    _logger.info(f"FSM: Auto-created Service Order for {order.partner_id.name} from SO {order.name}")

        return res

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fsm_order_ids = fields.One2many('sentinela.fsm.order', 'sale_order_id', string='Órdenes de Servicio')
    fsm_order_count = fields.Integer(string='# Órdenes de Servicio', compute='_compute_fsm_order_count')

    @api.depends('fsm_order_ids')
    def _compute_fsm_order_count(self):
        for order in self:
            order.fsm_order_count = len(order.fsm_order_ids)

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
                    'sale_order_id': order.id,
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
                    'sale_order_id': order.id,
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
                    ('state', 'in', ['active', 'closed', 'suspension'])
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

                    # Create the FSM Installation Order. El producto puede sobrescribir
                    # el tipo (p.ej. una póliza que se vende como 'maintenance').
                    fsm_type = line.product_id.fsm_service_type or 'install'
                    FsmOrder.create({
                        'partner_id': order.partner_id.id,
                        'service_address_id': order.partner_shipping_id.id or order.partner_id.id,
                        'subscription_id': new_sub.id,
                        'sale_order_id': order.id,
                        'service_type': fsm_type,
                        'description': f"INSTALACIÓN INICIAL: Servicio {line.product_id.name} vendido en orden {order.name}.<br/>Favor de realizar instalación física y capturar datos técnicos.",
                        'priority': '1',
                    })
                    _logger.info(f"FSM/SUB: Auto-created Installation flow for {order.partner_id.name}")

            # 4. AUTOMATION: One-time Service Orders (non-subscriptions) — OPT-IN.
            # Solo los productos marcados 'generates_fsm_order' disparan orden.
            # (Antes: heurístico por nombre que generaba órdenes basura para
            #  cualquier servicio, incluso cargos administrativos.)
            service_lines = order.order_line.filtered(
                lambda l: l.product_id.generates_fsm_order and not l.product_id.is_subscription)

            for s_line in service_lines:
                # Evitar duplicar si ya generamos una orden para este SO + producto recientemente.
                existing_fsm = FsmOrder.search([
                    ('sale_order_id', '=', order.id),
                    ('description', 'like', s_line.product_id.name),
                    ('create_date', '>=', fields.Datetime.now() - relativedelta(minutes=5))
                ], limit=1)

                if not existing_fsm:
                    fsm_type = s_line.product_id.fsm_service_type or 'other'
                    FsmOrder.create({
                        'partner_id': order.partner_id.id,
                        'service_address_id': order.partner_shipping_id.id or order.partner_id.id,
                        'sale_order_id': order.id,
                        'service_type': fsm_type,
                        'description': f"ORDEN DE SERVICIO TÉCNICO: {s_line.product_id.name} vendido en {order.name}.<br/>Realizar el trabajo solicitado y documentar.",
                        'priority': '0',
                    })
                    _logger.info(f"FSM: Auto-created Service Order ({fsm_type}) for {order.partner_id.name} from SO {order.name}")

        return res

    def action_view_fsm_orders(self):
        """ Smart button: muestra las órdenes de servicio originadas por esta venta. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Órdenes de Servicio'),
            'res_model': 'sentinela.fsm.order',
            'view_mode': 'list,form,calendar',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def action_open_generate_fsm_wizard(self):
        """ Botón: abre el asistente para crear una orden de servicio manual
        ligada a esta venta, eligiendo tipo / técnico / fecha. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generar Orden de Servicio'),
            'res_model': 'sentinela.fsm.generate.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_service_address_id': self.partner_shipping_id.id or self.partner_id.id,
            },
        }

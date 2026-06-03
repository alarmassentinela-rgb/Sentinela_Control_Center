from odoo import models, fields

# Tipos de orden que un producto puede disparar desde Ventas.
# 'patrol' se excluye a propósito: el patrullaje nace de un evento de alarma
# (sentinela_monitoring), no de una línea de venta.
FSM_SALE_SERVICE_TYPES = [
    ('install', 'Instalación'),
    ('repair', 'Reparación / Falla (Correctivo)'),
    ('maintenance', 'Mantenimiento Preventivo'),
    ('transfer', 'Traslado'),
    ('removal', 'Retiro de Equipo / Desinstalación'),
    ('other', 'Otro'),
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    generates_fsm_order = fields.Boolean(
        string='Genera Orden de Servicio',
        default=False,
        help='Si está activo, al CONFIRMAR una venta con este producto se crea '
             'automáticamente una orden de servicio en campo (FSM) del tipo indicado.')
    fsm_service_type = fields.Selection(
        FSM_SALE_SERVICE_TYPES,
        string='Tipo de Orden a Generar',
        default='install',
        help='Tipo de orden de servicio que se creará al vender este producto.')

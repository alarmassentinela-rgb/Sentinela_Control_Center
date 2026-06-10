from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta

class SentinelaSubscription(models.Model):
    _inherit = 'sentinela.subscription'

    fsm_order_ids = fields.One2many('sentinela.fsm.order', 'subscription_id', string='Órdenes de Servicio')
    fsm_order_count = fields.Integer(compute='_compute_fsm_order_count', string='# Tickets')

    all_fsm_evidence_ids = fields.Many2many('sentinela.fsm.evidence', string='Expediente de Evidencias', compute='_compute_all_fsm_evidence')

    # ---------------- Mantenimiento Preventivo (Pólizas) ----------------
    maintenance_frequency = fields.Selection([
        ('0', 'Sin mantenimiento programado'),
        ('1', 'Mensual'),
        ('3', 'Trimestral'),
        ('6', 'Semestral'),
        ('12', 'Anual'),
    ], string='Frecuencia de Mantenimiento', default='0', tracking=True,
        help='Cada cuántos meses se genera automáticamente una orden de mantenimiento preventivo.')
    next_maintenance_date = fields.Date(string='Próximo Mantenimiento', tracking=True,
        help='Fecha en que se generará la siguiente orden de mantenimiento preventivo. '
             'Se avanza automáticamente al generar cada orden.')
    last_maintenance_date = fields.Date(string='Último Mantenimiento', tracking=True, readonly=True,
        help='Se actualiza automáticamente al finalizar una orden de servicio técnico.')

    @api.depends('fsm_order_ids.evidence_ids')
    def _compute_all_fsm_evidence(self):
        for sub in self:
            sub.all_fsm_evidence_ids = sub.fsm_order_ids.mapped('evidence_ids')

    @api.depends('fsm_order_ids')
    def _compute_fsm_order_count(self):
        for sub in self:
            sub.fsm_order_count = len(sub.fsm_order_ids)

    def action_view_fsm_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tickets de Servicio',
            'res_model': 'sentinela.fsm.order',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id, 'default_partner_id': self.partner_id.id}
        }

    def action_reactivate_with_visit(self):
        """Reconecta el servicio (remoto) Y genera una orden de visita técnica
        para verificar señal/estado físico del CPE/equipo en sitio.

        Para los casos en que el reprovisioning remoto no basta y hay que mandar
        a alguien. La reconexión normal (action_reactivate) sigue siendo remota
        y NO genera orden — este botón es la vía explícita cuando se requiere visita.
        """
        self.ensure_one()
        # 1. Reconexión remota estándar (router/floLIVE/SentiCar + estado).
        self.action_reactivate()
        # 2. Orden de visita técnica.
        order = self.env['sentinela.fsm.order'].create({
            'partner_id': self.partner_id.id,
            'service_address_id': self.service_address_id.id or self.partner_id.id,
            'subscription_id': self.id,
            'service_type': 'repair',
            'priority': '2',  # Urgente
            'description': _(
                "RECONEXIÓN CON VISITA TÉCNICA: el servicio se reconectó. "
                "Acudir a verificar señal y estado físico del CPE/equipo en sitio."),
        })
        self.message_post(body=_(
            "🔧 <b>Reconexión con visita técnica:</b> se generó la orden de servicio "
            "<b>%s</b> para revisión en sitio.") % order.name)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orden de Servicio'),
            'res_model': 'sentinela.fsm.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def _cron_generate_preventive_maintenance(self):
        """ 
        Busca contratos que requieran mantenimiento preventivo 
        y crea las órdenes de servicio automáticamente.
        """
        today = fields.Date.today()
        # Buscar contratos cuya fecha de mantenimiento sea hoy o haya pasado
        subs_to_service = self.search([
            ('state', '=', 'active'),
            ('maintenance_frequency', '!=', '0'),
            ('next_maintenance_date', '<=', today)
        ])
        
        FsmOrder = self.env['sentinela.fsm.order']
        orders_created = 0

        for sub in subs_to_service:
            # Evitar duplicar si ya hay una orden de mantenimiento abierta (Nuevo, Asignado o En Proceso)
            existing_order = FsmOrder.search([
                ('subscription_id', '=', sub.id),
                ('service_type', '=', 'maintenance'),
                ('stage', 'in', ['new', 'assigned', 'in_progress', 'paused'])
            ], limit=1)

            if not existing_order:
                FsmOrder.create({
                    'partner_id': sub.partner_id.id,
                    'service_address_id': sub.service_address_id.id or sub.partner_id.id,
                    'subscription_id': sub.id,
                    'service_type': 'maintenance',
                    'priority': '0', # Normal
                    'description': f"MANTENIMIENTO PREVENTIVO PROGRAMADO: Basado en frecuencia {sub.maintenance_frequency} meses.<br/>Último servicio: {sub.last_maintenance_date or 'NUNCA'}",
                })
                orders_created += 1
                sub.message_post(body="AUTOMATIZACIÓN: Se ha generado una orden de mantenimiento preventivo automáticamente.")

            # Avanzar la fecha del próximo mantenimiento aunque ya existiera una orden abierta,
            # para no regenerar/reintentar todos los días mientras esa orden sigue en proceso.
            months = int(sub.maintenance_frequency)
            base = sub.next_maintenance_date or today
            sub.next_maintenance_date = base + relativedelta(months=months)

        return orders_created

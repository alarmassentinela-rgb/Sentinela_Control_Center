from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_subscription = fields.Boolean(string='Es Servicio de Suscripción', default=False)
    default_recurring_interval = fields.Selection([
        ('1', 'Mensual'),
        ('2', 'Bimestral'),
        ('3', 'Trimestral'),
        ('6', 'Semestral'),
        ('12', 'Anual')
    ], string='Ciclo de Facturación Predeterminado', default='1')
    
    # Mikrotik Integration
    mikrotik_profile_id = fields.Many2one('sentinela.mikrotik.profile', string='Perfil Mikrotik Vinculado', help="Select the speed profile managed by Odoo")
    
    # Categorization for filtering
    service_type = fields.Selection(selection_add=[
        ('internet', 'Internet WISP'),
        ('alarm', 'Monitoring Alarm'),
        ('gps', 'GPS Tracking'),
        ('maintenance', 'Maintenance Poliza')
    ], ondelete={'internet': 'cascade', 'alarm': 'cascade', 'gps': 'cascade', 'maintenance': 'cascade'})

    # Contratos
    contract_template_id = fields.Many2one(
        'sentinela.contract.template', 
        string='Plantilla de Contrato',
        help="Seleccione el diseño del contrato para este producto."
    )
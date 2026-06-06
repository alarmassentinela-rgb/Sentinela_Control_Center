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
        ('gps', 'Senticar (GPS)'),
        ('maintenance', 'Maintenance Poliza')
    ], ondelete={'internet': 'cascade', 'alarm': 'cascade', 'gps': 'cascade', 'maintenance': 'cascade'})

    service_inclusion_ids = fields.One2many('sentinela.product.service.inclusion', 'product_id', string='Matriz de Servicios Incluidos')

    # Contratos
    contract_template_id = fields.Many2one(
        'sentinela.contract.template',
        string='Plantilla de Contrato',
        help="Seleccione el diseño del contrato para este producto."
    )

    # GPS: el plan define el MODO (y con ello: si gestionamos la SIM y cómo se suspende)
    gps_mode = fields.Selection([
        ('vehiculo', 'GPS Vehículo (SIM nuestra)'),
        ('movil', 'Rastreo Móvil (SIM del cliente)'),
    ], string='Modo GPS',
        help="Solo para planes GPS. 'GPS Vehículo' = la SIM es nuestra (floLIVE) y SE CORTA al suspender. "
             "'Rastreo Móvil' = la SIM es del cliente y NUNCA se corta (solo se deshabilita el equipo en SentiCar).")
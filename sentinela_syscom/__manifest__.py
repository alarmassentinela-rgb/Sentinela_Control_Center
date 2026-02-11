{
    'name': 'Sentinela Syscom Integration',
    'version': '18.0.1.1.0',
    'category': 'Inventory/Syscom',
    'summary': 'Integración con API de Syscom para sincronización de catálogo, precios y stock.',
    'description': """
        Este módulo permite conectar Odoo con la API de Syscom.
        Funcionalidades:
        * Configuración de credenciales API.
        * Sincronización de productos bajo demanda (Buscador por modelo).
        * Actualización automática de precios y existencias.
    """,
    'author': 'Sentinela IT',
    'website': 'https://sentinela.mx',
    'depends': [
        'base',
        'stock',
        'product',
        'purchase',
        'sentinela_cfdi_prodigia',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_syscom.xml',
        'views/res_config_settings_views.xml',
        'views/product_views.xml',
        'wizard/syscom_import_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
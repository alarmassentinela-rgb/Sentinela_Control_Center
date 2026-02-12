{
    'name': 'Sentinela Monitoring System',
    'version': '18.0.1.0.0',
    'category': 'Industries/Security',
    'summary': 'Sistema de monitoreo de alarmas integrado con Odoo (similar o mejor que Securithor)',
    'description': """
Sistema completo de monitoreo de alarmas para centrales de monitoreo.
Características principales:
---------------------------
* Recepción de señales de alarma a través de API
* Dashboard en tiempo real para operadores
* Gestión de dispositivos de monitoreo
* Panel de control para clientes suscriptores
* Integración con módulo FSM para respuesta a alarmas
* Sistema de notificaciones automático
* Informes y estadísticas detalladas
* Mapas integrados para ubicación de alarmas
* Botones de pánico virtuales
""",
    'author': 'Sentinela IT',
    'website': 'https://sentinela.mx',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'account',
        'sentinela_subscriptions',
        'sentinela_fsm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/alarm_codes_data.xml',
        'wizard/alarm_handle_wizard_views.xml',
        'views/monitoring_device_views.xml',
        'views/alarm_event_views.xml',
        'views/alarm_signal_views.xml',
        'views/response_team_views.xml',
        'views/alarm_code_views.xml',
        'views/alarm_priority_views.xml', # AGREGADO
        'views/subscription_views_extension.xml',
        'views/monitoring_zone_views.xml',
        'views/monitoring_menu.xml', # AGREGADO
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sentinela_monitoring/static/src/xml/monitoring_dashboard.xml',
            'sentinela_monitoring/static/src/js/alarm_service.js',
            'sentinela_monitoring/static/src/js/monitoring_dashboard.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
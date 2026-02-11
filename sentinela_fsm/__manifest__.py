{
    'name': 'Gestion de Servicios',
    'version': '18.0.1.0.0',
    'category': 'Services/Field Service',
    'summary': 'Gestión de órdenes de servicio en campo (Instalaciones, Reparaciones).',
    'description': """
        Módulo FSM para Sentinela.
        Reemplazo de 2Worker/Auvo.
        Características:
        - Gestión de Órdenes de Trabajo.
        - Agenda y Calendario de Técnicos.
        - Geolocalización y Check-in.
        - Evidencia Fotográfica y Firma Digital.
        - Seguimiento de Tiempo y Productividad.
        - Gestión de Inventarios y Repuestos.
        - Calificación del Servicio.
        - Notificaciones Push.
        - Comunicación Cliente-Técnico.
        - Optimización de Rutas.
    """,
    'author': 'Sentinela IT',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'sentinela_subscriptions',
        'base_automation',
        'stock',
    ],
    'external_dependencies': {
        'python': ['geopy'],
    },
    'data': [
        'security/fsm_security.xml',
        'security/ir.model.access.csv',
        'wizard/fsm_order_pause_wizard_views.xml',
        'wizard/fsm_chat_send_message_wizard_views.xml',
        'wizard/fsm_create_route_wizard_views.xml',
        'data/ir_sequence_data.xml',
        'data/fsm_demo_data.xml',
        'data/product_demo_data.xml',
        'data/mail_template_data.xml',
        'data/fsm_automation_data.xml',
        'views/fsm_order_views.xml',
        'views/fsm_equipment_views.xml',
        'views/fsm_dashboard_views.xml',
        'views/fsm_notification_views.xml',
        'views/fsm_chat_views.xml',
        'views/fsm_route_optimization_views.xml',
        'views/subscription_views.xml',
        'views/fsm_pause_reason_views.xml',
        'views/fsm_menus.xml',
        'views/fsm_portal_templates.xml',
        'report/fsm_order_report.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}

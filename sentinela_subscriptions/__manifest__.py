{
    'name': 'Sentinela Subscriptions & Recurring Billing',
    'version': '18.0.1.4.0',
    'category': 'Sales/Subscriptions',
    'summary': 'Gestión avanzada de membresías, facturación recurrente y aprovisionamiento técnico para Sentinela.',
    'description': """
        Módulo personalizado para Sentinela Alarmas & Servicios.
        Características Principales:
        ---------------------------
        * Gestión de Suscripciones (Alarmas, Internet, GPS).
        * Facturación Recurrente Automatizada (Cron).
        * Prorrateo automático en cambios de plan (Upgrades/Downgrades).
        * Doble Estado: Financiero (Pagado/Mora) y Técnico (Activo/Suspendido).
        * Ganchos para integración con Mikrotik (Suspensión automática).
        * Gestión de Contratos Forzosos y Equipos en Comodato.
        * Notificaciones automatizadas de cobranza (Email/Webhook n8n).
    """,
    'author': 'Sentinela IT',
    'website': 'https://sentinela.mx',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'account',
        'stock',  # Para gestión de equipos serializados
        'product',
        'sentinela_digital_sign',
    ],
                'data': [
                    'security/subscription_security.xml',
                    'security/ir.model.access.csv',
                    'data/ir_sequence_data.xml',
            
                'data/ir_cron_data.xml',
                'data/product_data.xml',
                'data/mail_template_extension_data.xml',
                'report/contract_report.xml',
                'wizard/mikrotik_traffic_views.xml',
                'wizard/subscription_transfer_views.xml',
                'wizard/subscription_extension_wizard_views.xml',
                'wizard/subscription_close_wizard_views.xml',
                'views/subscription_views.xml',
                'views/contract_template_views.xml',
                'views/res_partner_views.xml',
                'views/product_views.xml',
                'views/account_move_views.xml',
                'views/router_views.xml',
                'views/mikrotik_profile_views.xml',
                'views/menus.xml',
            ],
            'assets': {
                'web.assets_backend': [
                    'sentinela_subscriptions/static/src/**/*',
                ],
            },
            'installable': True,    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

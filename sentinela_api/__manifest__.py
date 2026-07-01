{
    'name': 'Sentinela API (Portal COC)',
    'version': '18.0.0.3.1',
    'category': 'Sentinela/Portal',
    'summary': 'Capa REST/JSON del Centro de Operaciones del Cliente (COC). '
               'Serializa y expone los modulos sentinela_* al portal web y a la app movil. '
               'NO duplica logica de negocio: reutiliza los metodos de modelo existentes.',
    'author': 'Sentinela IT',
    'depends': [
        'base', 'web', 'portal', 'mail',
        'sentinela_subscriptions',
        'sentinela_monitoring',
        'sentinela_fsm',
        'sentinela_cfdi_prodigia',
        'sentinela_digital_sign',
    ],
    'data': [
        'security/portal_security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

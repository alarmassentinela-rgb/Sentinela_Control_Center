{
    'name': 'Firma Digital Sentinela',
    'version': '18.0.1.0.0',
    'category': 'Document Management',
    'summary': 'Permite a clientes firmar documentos PDF desde el portal.',
    'author': 'Sentinela IT',
    'depends': ['base', 'mail', 'portal', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'views/sign_document_views.xml',
        'views/sign_portal_templates.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # Aquí podríamos agregar estilos CSS específicos si fuera necesario
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}

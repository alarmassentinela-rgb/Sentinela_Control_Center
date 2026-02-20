from odoo import models, fields, api

class SentinelaSubscriptionSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    connecta_client_id = fields.Char(
        string='Connecta Client ID (Correo)',
        config_parameter='sentinela.connecta_client_id',
        help="El correo electrónico usado para entrar al portal de Connecta/floLIVE."
    )
    connecta_access_token = fields.Char(
        string='Connecta Access Token (Contraseña)',
        config_parameter='sentinela.connecta_access_token',
        help="La contraseña usada para entrar al portal de Connecta/floLIVE."
    )

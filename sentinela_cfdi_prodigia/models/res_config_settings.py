from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    prodigia_api_url = fields.Char(
        string='Prodigia API URL',
        config_parameter='sentinela_cfdi_prodigia.api_url',
        default='https://facturacion.pade.mx/api/v1',
    )
    prodigia_user = fields.Char(
        string='Prodigia Usuario',
        config_parameter='sentinela_cfdi_prodigia.user',
    )
    prodigia_password = fields.Char(
        string='Prodigia Contraseña',
        config_parameter='sentinela_cfdi_prodigia.password',
    )
    prodigia_rfc = fields.Char(
        string='RFC Emisor',
        config_parameter='sentinela_cfdi_prodigia.rfc',
    )
    prodigia_contract = fields.Char(
        string='Prodigia Contrato',
        config_parameter='sentinela_cfdi_prodigia.contract',
    )
    prodigia_client_code = fields.Char(
        string='Prodigia Código de Cliente',
        config_parameter='sentinela_cfdi_prodigia.client_code',
    )
    prodigia_test_mode = fields.Boolean(
        string='Modo de Prueba Prodigia',
        config_parameter='sentinela_cfdi_prodigia.test_mode',
        default=True,
        help='Si está activo, los CFDI se timbrarán en modo de prueba en Prodigia.'
    )



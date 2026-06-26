# -*- coding: utf-8 -*-
"""GET /v1/config/theme — branding del portal (COSTURA multiempresa).

Publico (sin sesion). En v1 devuelve el branding de Sentinela leido de
ir.config_parameter; a futuro un resolver puede devolverlo por hostname/inquilino
sin cambiar el contrato (single-tenant ahora, multi-tenant despues).
"""
from odoo import http
from odoo.http import request

from .main import API_PREFIX, json_ok


class ConfigController(http.Controller):

    @http.route(API_PREFIX + '/config/theme', type='http', auth='public', methods=['GET'], csrf=False)
    def theme(self, **kw):
        icp = request.env['ir.config_parameter'].sudo()
        data = {
            'app_name': icp.get_param('sentinela_api.brand_name', 'Sentinela'),
            'logo_url': icp.get_param('sentinela_api.brand_logo_url', ''),
            'primary_color': icp.get_param('sentinela_api.brand_primary', '#0B5FFF'),
            'support_phone': icp.get_param('sentinela_api.support_phone', ''),
            'support_whatsapp': icp.get_param('sentinela_api.support_whatsapp', ''),
        }
        return json_ok(data)

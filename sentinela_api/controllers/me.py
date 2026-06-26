# -*- coding: utf-8 -*-
"""GET /v1/me — perfil del cliente autenticado.

auth='user': corre como el usuario portal (Opcion A). Devuelve UNICAMENTE el partner
del usuario en sesion; el aislamiento entre clientes lo garantizan las record rules.
"""
from odoo import http
from odoo.http import request

from .main import API_PREFIX, json_ok
from ..lib.serializers import serialize_partner


class MeController(http.Controller):

    @http.route(API_PREFIX + '/me', type='http', auth='user', methods=['GET'], csrf=False)
    def me(self, **kw):
        partner = request.env.user.partner_id
        return json_ok(serialize_partner(partner))

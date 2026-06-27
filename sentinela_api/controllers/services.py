# -*- coding: utf-8 -*-
"""GET /v1/services — Mis Servicios (suscripciones del cliente).

auth='user': corre como el usuario portal. El aislamiento entre clientes lo
garantizan las record rules (WS-2): `search` solo devuelve lo del cliente, y el
detalle por id se resuelve via `search` (no `browse`) para que la regla aplique
y un id ajeno devuelva 404 (anti-IDOR).
"""
from odoo import http
from odoo.http import request

from .main import API_PREFIX, json_ok, problem
from ..lib.serializers import serialize_subscription


class ServicesController(http.Controller):

    @http.route(API_PREFIX + '/services', type='http', auth='user', methods=['GET'], csrf=False)
    def services(self, **kw):
        subs = request.env['sentinela.subscription'].search([], order='service_type, name')
        # Propiedad ya garantizada por la record rule (el search filtra); sudo solo
        # para leer campos relacionados (plan/product, direccion) sin chocar con ACLs.
        return json_ok({'items': [serialize_subscription(s.sudo()) for s in subs], 'count': len(subs)})

    @http.route(API_PREFIX + '/services/<int:service_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def service_detail(self, service_id, **kw):
        sub = request.env['sentinela.subscription'].search([('id', '=', service_id)], limit=1)
        if not sub:
            return problem(404, 'Servicio no encontrado')
        return json_ok(serialize_subscription(sub.sudo()))

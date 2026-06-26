# -*- coding: utf-8 -*-
"""Base de la capa REST del COC: prefijo de version, respuestas JSON y errores RFC-7807.

Convencion: cada recurso vive en su propio archivo de controller (me.py, config.py, ...)
y NO contiene logica de negocio: invoca metodos de modelo existentes de sentinela_* y
serializa con lib/serializers.py. El scoping por cliente lo garantizan las record rules
de Odoo (usuario portal lazy, Opcion A) como PRIMERA linea de defensa.
"""
import logging
import uuid

from odoo.http import request

_logger = logging.getLogger('sentinela_api')

API_PREFIX = '/v1'


def get_request_id():
    """Correlacion de logs/trazas (WS-8). Reusa el header entrante o genera uno."""
    return request.httprequest.headers.get('X-Request-Id') or uuid.uuid4().hex


def json_ok(data, status=200):
    """Respuesta JSON estandar con X-Request-Id para trazabilidad."""
    resp = request.make_json_response(data, status=status)
    resp.headers['X-Request-Id'] = get_request_id()
    return resp


def problem(status, title, detail=None, type_='about:blank'):
    """Error en formato RFC-7807 (application/problem+json)."""
    body = {'type': type_, 'title': title, 'status': status}
    if detail:
        body['detail'] = detail
    resp = request.make_json_response(body, status=status)
    resp.headers['Content-Type'] = 'application/problem+json'
    resp.headers['X-Request-Id'] = get_request_id()
    return resp

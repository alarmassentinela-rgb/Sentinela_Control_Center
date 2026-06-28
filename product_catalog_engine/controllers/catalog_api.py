"""Catalog Public Interface — implementación REST v1 del contrato público.

REST es la PRIMERA implementación; la lógica vive en la capa de servicios
(`lib/api_service`), no aquí (Filosofía §14: no duplicar lógica → GraphQL futuro).
Transversales: API key, scopes, rate limit, idempotencia, X-Request-ID/X-Correlation-ID,
paginación/filtros/orden, gzip, OpenAPI/Swagger, códigos de error documentados.
"""
from __future__ import annotations

import gzip
import json
import logging
import uuid

import werkzeug

from odoo import http
from odoo.http import request

from ..lib import api_service
from ..lib import openapi_spec as oas

_logger = logging.getLogger(__name__)
BASE = "/catalog/api/v1"


def _ids():
    rid = uuid.uuid4().hex
    cid = request.httprequest.headers.get("X-Correlation-ID") or uuid.uuid4().hex
    return rid, cid


def _make(payload, status=200, extra=None):
    rid, cid = _ids()
    body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    headers = [("Content-Type", "application/json; charset=utf-8"),
               ("X-Request-ID", rid), ("X-Correlation-ID", cid)]
    if "gzip" in (request.httprequest.headers.get("Accept-Encoding") or "") and len(body) > 512:
        body = gzip.compress(body)
        headers.append(("Content-Encoding", "gzip"))
    if extra:
        headers += list(extra.items())
    return werkzeug.wrappers.Response(body, status=status, headers=headers)


def _error(code, message, status=None, extra=None):
    rid, cid = _ids()
    st = status or oas.ERROR_CODES.get(code, 400)
    body = json.dumps({"error": {"code": code, "message": message, "request_id": rid}}).encode("utf-8")
    headers = [("Content-Type", "application/json"), ("X-Request-ID", rid), ("X-Correlation-ID", cid)]
    if extra:
        headers += list(extra.items())
    return werkzeug.wrappers.Response(body, status=st, headers=headers)


def _bearer():
    auth = request.httprequest.headers.get("Authorization") or ""
    return auth[7:] if auth.startswith("Bearer ") else None


def _authn(scope="read"):
    """Devuelve (key_record, None) o (None, error_response)."""
    raw = request.httprequest.headers.get("X-API-Key") or _bearer()
    key = request.env["catalog.api.key"].sudo().authenticate(raw)
    if not key:
        return None, _error("unauthorized", "API key inválida o ausente")
    if scope and not key.has_scope(scope):
        return None, _error("forbidden", "Falta el scope requerido: %s" % scope)
    allowed, remaining, reset = key.consume()
    rl_headers = {"X-RateLimit-Limit": str(key.rate_limit_per_min),
                  "X-RateLimit-Remaining": str(remaining), "X-RateLimit-Reset": str(reset)}
    if not allowed:
        return None, _error("rate_limited", "Límite de peticiones excedido",
                            extra=dict(rl_headers, **{"Retry-After": str(reset)}))
    return key, None


def _svc():
    return api_service.CatalogApiService(request.env(su=True))


class CatalogPublicAPI(http.Controller):

    # ---- documentación (abierta) ----
    @http.route(BASE + "/openapi.json", auth="public", type="http", methods=["GET"], csrf=False)
    def openapi(self, **kw):
        return _make(oas.build_openapi())

    @http.route(BASE + "/schema/product.json", auth="public", type="http", methods=["GET"], csrf=False)
    def product_schema(self, **kw):
        return _make(oas.product_json_schema())

    @http.route(BASE + "/docs", auth="public", type="http", methods=["GET"], csrf=False)
    def docs(self, **kw):
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>Catalog API</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css"></head>
<body><div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
<script>window.onload=function(){SwaggerUIBundle({url:'%s/openapi.json',dom_id:'#swagger-ui'})}</script>
</body></html>""" % BASE
        return werkzeug.wrappers.Response(html, status=200,
                                          headers=[("Content-Type", "text/html; charset=utf-8")])

    @http.route(BASE + "/health", auth="public", type="http", methods=["GET"], csrf=False)
    def health(self, **kw):
        return _make(_svc().health())

    # ---- recursos (requieren API key) ----
    @http.route(BASE + "/products", auth="public", type="http", methods=["GET"], csrf=False)
    def products(self, **kw):
        key, err = _authn("read")
        if err:
            return err
        try:
            filters = {k: kw.get(k) for k in api_service.PUBLIC_FILTERS if kw.get(k)}
            result = _svc().search(q=kw.get("q"), filters=filters, page=kw.get("page", 1),
                                   page_size=kw.get("page_size", 50), sort=kw.get("sort", "id"))
            return _make(result)
        except Exception as e:  # noqa: BLE001
            _logger.exception("API /products")
            return _error("internal_error", str(e))

    @http.route(BASE + "/products/<string:ref>", auth="public", type="http", methods=["GET"], csrf=False)
    def product_detail(self, ref, **kw):
        key, err = _authn("read")
        if err:
            return err
        try:
            dto = _svc().get_product(ref, backend=kw.get("backend"))
            if not dto:
                return _error("not_found", "Producto no encontrado: %s" % ref)
            return _make(dto)
        except Exception as e:  # noqa: BLE001
            _logger.exception("API /products/%s", ref)
            return _error("internal_error", str(e))

    @http.route(BASE + "/products/<string:ref>/promote", auth="public", type="http",
                methods=["POST"], csrf=False)
    def promote(self, ref, **kw):
        key, err = _authn("promote")
        if err:
            return err
        Idem = request.env["catalog.api.idempotency"].sudo()
        idem = request.httprequest.headers.get("Idempotency-Key")
        try:
            if idem:
                prev = Idem.fetch(idem)
                if prev:
                    return _make(json.loads(prev["response"] or "{}"), status=prev["status_code"] or 200)
            res = _svc().promote(ref, backend=kw.get("backend"))
            if not res:
                return _error("not_found", "Producto no encontrado: %s" % ref)
            if idem:
                Idem.store(idem, "promote", 200, json.dumps(res, default=str))
            return _make(res)
        except Exception as e:  # noqa: BLE001
            _logger.exception("API promote %s", ref)
            return _error("internal_error", str(e))

    @http.route(BASE + "/metrics", auth="public", type="http", methods=["GET"], csrf=False)
    def metrics(self, **kw):
        key, err = _authn("read")
        if err:
            return err
        return _make(_svc().metrics())

"""OpenAPI 3 + JSON Schema de la Catalog Public Interface (v1). Se sirve en
/catalog/api/v1/openapi.json y Swagger UI en /catalog/api/v1/docs.
"""
from __future__ import annotations

API_BASE = "/catalog/api/v1"

PRODUCT_SCHEMA = {
    "type": "object",
    "properties": {
        "distributor_product_id": {"type": "string"},
        "backend": {"type": "string"},
        "name": {"type": "string"},
        "brand": {"type": ["string", "null"]},
        "manufacturer": {"type": ["string", "null"]},
        "distributor_sku": {"type": ["string", "null"]},
        "manufacturer_sku": {"type": ["string", "null"]},
        "barcode": {"type": ["string", "null"]},
        "sat_code": {"type": ["string", "null"]},
        "category_path": {"type": ["string", "null"]},
        "price": {"type": "object", "properties": {
            "list": {"type": ["number", "null"]}, "cost": {"type": ["number", "null"]},
            "currency": {"type": "string"}}},
        "stock": {"type": "object", "properties": {"total": {"type": "integer"}}},
        "thumb_url": {"type": ["string", "null"]},
        "freshness": {"type": "object", "properties": {
            "status": {"type": "string", "enum": ["never", "fresh", "expired"]}}},
        "product_master_id": {"type": ["integer", "null"]},
        "is_promoted": {"type": "boolean"},
    },
    "required": ["distributor_product_id", "backend", "name"],
}

ERROR_SCHEMA = {
    "type": "object",
    "properties": {"error": {"type": "object", "properties": {
        "code": {"type": "string"}, "message": {"type": "string"},
        "request_id": {"type": "string"}}}},
}

# Catálogo de códigos de error documentados.
ERROR_CODES = {
    "invalid_request": 400, "unauthorized": 401, "forbidden": 403,
    "not_found": 404, "conflict": 409, "unprocessable": 422,
    "rate_limited": 429, "internal_error": 500, "upstream_unavailable": 503,
}


def product_json_schema():
    return dict(PRODUCT_SCHEMA, **{"$schema": "https://json-schema.org/draft/2020-12/schema",
                                   "title": "CatalogProduct"})


def build_openapi():
    page = {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}}
    size = {"name": "page_size", "in": "query", "schema": {"type": "integer", "default": 50, "maximum": 200}}
    return {
        "openapi": "3.0.3",
        "info": {"title": "Catalog Public Interface", "version": "1.0.0",
                 "description": "Interfaz pública del Motor de Catálogo (Alea Systems). "
                                "REST es la primera implementación del contrato; el contrato "
                                "público es estable (v1)."},
        "servers": [{"url": API_BASE}],
        "components": {
            "securitySchemes": {"ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}},
            "schemas": {"Product": PRODUCT_SCHEMA, "Error": ERROR_SCHEMA},
            "parameters": {},
        },
        "security": [{"ApiKeyAuth": []}],
        "paths": {
            "/health": {"get": {"summary": "Liveness", "security": [],
                                "responses": {"200": {"description": "OK"}}}},
            "/openapi.json": {"get": {"summary": "Esta especificación", "security": [],
                                      "responses": {"200": {"description": "OpenAPI"}}}},
            "/products": {"get": {
                "summary": "Buscar productos (filtros, orden, paginación)",
                "parameters": [
                    {"name": "q", "in": "query", "schema": {"type": "string"}},
                    {"name": "backend", "in": "query", "schema": {"type": "string"}},
                    {"name": "brand", "in": "query", "schema": {"type": "string"}},
                    {"name": "sat_code", "in": "query", "schema": {"type": "string"}},
                    {"name": "barcode", "in": "query", "schema": {"type": "string"}},
                    {"name": "sort", "in": "query", "schema": {"type": "string"},
                     "description": "campo o -campo (name, brand, price_list, stock_total, id)"},
                    page, size],
                "responses": {"200": {"description": "Lista paginada", "content": {"application/json": {
                    "schema": {"type": "object", "properties": {
                        "data": {"type": "array", "items": {"$ref": "#/components/schemas/Product"}},
                        "pagination": {"type": "object"}}}}}},
                    "401": {"description": "No autorizado"}, "429": {"description": "Rate limit"}}}},
            "/products/{ref}": {"get": {
                "summary": "Detalle de producto (refresca si está vencido)",
                "parameters": [{"name": "ref", "in": "path", "required": True, "schema": {"type": "string"}},
                               {"name": "backend", "in": "query", "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Producto", "content": {"application/json": {
                    "schema": {"$ref": "#/components/schemas/Product"}}}}, "404": {"description": "No existe"}}}},
            "/products/{ref}/promote": {"post": {
                "summary": "Promover a Producto Maestro (idempotente con Idempotency-Key)",
                "parameters": [{"name": "ref", "in": "path", "required": True, "schema": {"type": "string"}},
                               {"name": "Idempotency-Key", "in": "header", "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Maestro"}, "404": {"description": "No existe"}}}},
            "/metrics": {"get": {"summary": "Métricas del motor",
                                 "responses": {"200": {"description": "OK"}}}},
        },
    }

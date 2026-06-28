"""API keys, rate limiting e idempotencia de la Catalog Public Interface (D3c)."""
from __future__ import annotations

import secrets

from odoo import api, fields, models


class CatalogApiKey(models.Model):
    _name = "catalog.api.key"
    _description = "API Key del Motor de Catálogo"
    _order = "name"

    name = fields.Char(required=True)
    key = fields.Char(required=True, index=True, copy=False, default=lambda s: secrets.token_urlsafe(32))
    active = fields.Boolean(default=True)
    scopes = fields.Char(default="read", help="Lista separada por comas: read, promote.")
    rate_limit_per_min = fields.Integer(default=120, string="Límite (req/min)")
    window_start = fields.Datetime(copy=False)
    window_count = fields.Integer(copy=False, default=0)
    last_used_at = fields.Datetime(copy=False)

    _sql_constraints = [("key_uniq", "unique(key)", "API key duplicada.")]

    @api.model
    def authenticate(self, raw_key):
        if not raw_key:
            return False
        return self.sudo().search([("key", "=", raw_key), ("active", "=", True)], limit=1)

    def has_scope(self, scope):
        self.ensure_one()
        return scope in (self.scopes or "").replace(" ", "").split(",")

    def consume(self):
        """Token por ventana de 60 s. Devuelve (permitido, restantes, reset_segundos)."""
        self.ensure_one()
        now = fields.Datetime.now()
        if not self.window_start or (now - self.window_start).total_seconds() >= 60:
            self.window_start = now
            self.window_count = 0
        self.window_count += 1
        self.last_used_at = now
        remaining = max(0, self.rate_limit_per_min - self.window_count)
        reset = max(0, 60 - int((now - self.window_start).total_seconds()))
        return self.window_count <= self.rate_limit_per_min, remaining, reset


class CatalogApiIdempotency(models.Model):
    _name = "catalog.api.idempotency"
    _description = "Registro de idempotencia de la API de Catálogo"
    _order = "id desc"

    key = fields.Char(required=True, index=True, copy=False)
    endpoint = fields.Char()
    status_code = fields.Integer()
    response = fields.Text()

    _sql_constraints = [("idem_key_uniq", "unique(key)", "Idempotency-Key duplicada.")]

    @api.model
    def fetch(self, key):
        """Devuelve {status_code, response} o None. Lectura por SQL crudo: en el contexto
        público del controlador, el ORM (aun con sudo) lanza MissingError por record-rules."""
        if not key:
            return None
        self.env.cr.execute(
            "SELECT status_code, response FROM catalog_api_idempotency WHERE key=%s LIMIT 1", (key,))
        row = self.env.cr.fetchone()
        return {"status_code": row[0], "response": row[1]} if row else None

    @api.model
    def store(self, key, endpoint, status_code, response):
        if not key:
            return
        self.sudo().create({"key": key, "endpoint": endpoint,
                            "status_code": status_code, "response": response})

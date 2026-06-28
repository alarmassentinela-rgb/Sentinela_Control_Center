"""catalog.cache.entry — almacén del backend de caché PostgreSQL (key/value/TTL).
Es UN backend posible; la caché es reemplazable (ver lib/cache.py). El Motor no
depende de este modelo directamente, sino de la interfaz CacheBackend.
"""
from __future__ import annotations

from odoo import fields, models


class CatalogCacheEntry(models.Model):
    _name = "catalog.cache.entry"
    _description = "Entrada de caché del Motor de Catálogo (backend PostgreSQL)"

    key = fields.Char(required=True, index=True)
    value = fields.Text()
    expires_at = fields.Datetime(index=True)

    _sql_constraints = [("key_uniq", "unique(key)", "Clave de caché duplicada.")]

    def is_fresh(self):
        self.ensure_one()
        return not self.expires_at or self.expires_at > fields.Datetime.now()

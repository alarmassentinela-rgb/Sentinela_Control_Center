"""Políticas de sincronización por tipo de dato (concepto #2 de D3d).

Cada tipo de dato tiene su propio TTL (no un único cron para todo). Configurable por
distribuidor o global, SIN tocar código. El scheduler las consulta para decidir vigencia.

Canales operativos (por granularidad de la API):
  - price       (del listado, barato)            → 24 h por defecto
  - stock       (del listado, volátil)           → 30 min
  - enrichment  (del detalle: imágenes/docs/      → 30 d
                 garantía/descripción)
Las políticas de imágenes/docs (30 d) y garantía/descripción (90 d) que pediste
pertenecen al canal `enrichment` (una sola llamada de detalle las trae juntas); se
documenta la equivalencia y el modelo admite agregar tipos sin código si se requiere
mayor granularidad.
"""
from __future__ import annotations

from odoo import api, fields, models

DEFAULT_TTL = {"price": 1440, "stock": 30, "enrichment": 43200}


class CatalogSyncPolicy(models.Model):
    _name = "catalog.sync.policy"
    _description = "Política de sincronización por tipo de dato"
    _order = "backend_id, data_type"

    data_type = fields.Selection(
        [("price", "Precio"), ("stock", "Existencia"), ("enrichment", "Enriquecimiento")],
        required=True, string="Tipo de dato")
    backend_id = fields.Many2one(
        "distributor.backend", ondelete="cascade", index=True,
        string="Distribuidor", help="Vacío = política GLOBAL (aplica a todos los distribuidores).")
    ttl_minutes = fields.Integer(required=True, string="Vigencia (min)")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("policy_uniq", "unique(data_type, backend_id)",
         "Ya existe una política para ese tipo de dato y distribuidor."),
    ]

    @api.model
    def _ttl(self, data_type, backend=None):
        """TTL en minutos: específico del distribuidor → global → default de código."""
        Policy = self.sudo()
        if backend:
            p = Policy.search([("data_type", "=", data_type), ("backend_id", "=", backend.id)], limit=1)
            if p:
                return p.ttl_minutes
        p = Policy.search([("data_type", "=", data_type), ("backend_id", "=", False)], limit=1)
        if p:
            return p.ttl_minutes
        return DEFAULT_TTL.get(data_type, 1440)

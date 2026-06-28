"""Dashboard del estado del Motor de Catálogo (concepto #6 de D3d).

Panel con la salud del motor: indexados, promovidos, frescura, backlog, tiempos de
sincronización, errores, eventos, caché y desglose por distribuidor.
"""
from __future__ import annotations

from odoo import api, fields, models


class CatalogDashboard(models.TransientModel):
    _name = "catalog.dashboard"
    _description = "Estado del Motor de Catálogo"

    items_indexed = fields.Integer(string="Productos indexados", readonly=True)
    items_promoted = fields.Integer(string="Productos promovidos", readonly=True)
    items_fresh = fields.Integer(string="Vigentes", readonly=True)
    items_expired = fields.Integer(string="Expirados (backlog)", readonly=True)
    items_never = fields.Integer(string="Sin sincronizar", readonly=True)
    tier_summary = fields.Text(string="Por prioridad (tier)", readonly=True)
    avg_sync_ms = fields.Float(string="Tiempo prom. de sync (ms)", readonly=True)
    runs_error_24h = fields.Integer(string="Corridas con error (24h)", readonly=True)
    events_24h = fields.Integer(string="Eventos (24h)", readonly=True)
    cache_entries = fields.Integer(string="Entradas de caché", readonly=True)
    by_distributor = fields.Text(string="Por distribuidor", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res.update(self._collect())
        return res

    @api.model
    def _collect(self):
        Item = self.env["distributor.catalog.item"]
        Run = self.env["catalog.run"]
        Event = self.env["catalog.event"]
        now = fields.Datetime.now()
        day_ago = fields.Datetime.subtract(now, days=1)

        expired_or = ["|", "|", ("price_expires_at", "<=", now),
                      ("stock_expires_at", "<=", now), ("enrichment_expires_at", "<=", now)]
        indexed = Item.search_count([])
        expired = Item.search_count(expired_or)
        never = Item.search_count([("price_synced_at", "=", False),
                                   ("stock_synced_at", "=", False),
                                   ("enrichment_synced_at", "=", False)])
        tiers = {t: Item.search_count([("sync_tier", "=", t)]) for t in ("0", "1", "2", "3", "4")}
        runs = Run.search([("operation", "=", "sync"), ("duration_ms", ">", 0)], limit=200)
        avg_ms = round(sum(runs.mapped("duration_ms")) / len(runs), 1) if runs else 0.0

        # desglose por distribuidor
        lines = []
        for b in self.env["distributor.backend"].search([]):
            n = Item.search_count([("backend_id", "=", b.id)])
            ex = Item.search_count(["&", ("backend_id", "=", b.id)] + expired_or)
            if n:
                lines.append("%s: %d indexados, %d expirados" % (b.name, n, ex))

        return {
            "items_indexed": indexed,
            "items_promoted": Item.search_count([("product_tmpl_id", "!=", False)]),
            "items_fresh": indexed - expired,
            "items_expired": expired,
            "items_never": never,
            "tier_summary": "T0=%(0)s · T1=%(1)s · T2=%(2)s · T3=%(3)s · T4=%(4)s" % tiers,
            "avg_sync_ms": avg_ms,
            "runs_error_24h": Run.search_count([("state", "=", "error"), ("date_start", ">=", day_ago)]),
            "events_24h": Event.search_count([("occurred_at", ">=", day_ago)]),
            "cache_entries": self.env["catalog.cache.entry"].search_count([]),
            "by_distributor": "\n".join(lines) or "—",
        }

    def action_refresh(self):
        self.ensure_one()
        self.write(self._collect())
        return {"type": "ir.actions.act_window", "res_model": "catalog.dashboard",
                "res_id": self.id, "view_mode": "form", "target": "new"}

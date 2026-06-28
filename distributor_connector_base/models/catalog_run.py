"""Observabilidad (R2/R7): catalog.run (una corrida) + catalog.metric (mediciones).
Toda operación del motor abre un run, registra métricas y contadores, y cierra.
"""
from __future__ import annotations

from odoo import api, fields, models


class CatalogRun(models.Model):
    _name = "catalog.run"
    _description = "Corrida del Motor de Catálogo"
    _order = "date_start desc"

    name = fields.Char(compute="_compute_name")
    backend_id = fields.Many2one("distributor.backend", ondelete="set null", index=True)
    operation = fields.Selection(
        [("sync", "Sincronización"), ("search", "Búsqueda"), ("get_product", "Detalle"),
         ("price_stock", "Precio/Stock"), ("promote", "Promoción"), ("other", "Otro")],
        default="other", required=True, index=True)
    source = fields.Selection(
        [("cron", "Cron"), ("api", "API"), ("wizard", "Asistente"), ("user", "Usuario"),
         ("system", "Sistema")], default="system")
    state = fields.Selection(
        [("running", "En curso"), ("done", "Terminado"), ("error", "Error")],
        default="running", index=True)
    date_start = fields.Datetime(default=fields.Datetime.now, index=True)
    date_end = fields.Datetime()
    duration_ms = fields.Float(string="Duración (ms)")

    # Contadores (R2)
    api_calls = fields.Integer()
    products_synced = fields.Integer()
    products_promoted = fields.Integer()
    products_discarded = fields.Integer()
    errors = fields.Integer()
    cache_hits = fields.Integer()
    cache_misses = fields.Integer()
    quota_used = fields.Integer(string="Cuota consumida")
    message = fields.Text()
    metric_ids = fields.One2many("catalog.metric", "run_id")

    @api.depends("operation", "backend_id", "date_start")
    def _compute_name(self):
        for r in self:
            r.name = "%s · %s · %s" % (
                r.backend_id.name or "—", r.operation or "—",
                fields.Datetime.to_string(r.date_start) if r.date_start else "")

    def finish(self, state="done", message=None):
        """Cierra la corrida calculando duración."""
        for r in self:
            end = fields.Datetime.now()
            vals = {"state": state, "date_end": end}
            if r.date_start:
                vals["duration_ms"] = (end - r.date_start).total_seconds() * 1000.0
            if message is not None:
                vals["message"] = message
            r.write(vals)
        return True

    def log_metric(self, name, value_ms, ref=None):
        self.ensure_one()
        return self.env["catalog.metric"].create({
            "run_id": self.id, "name": name, "value_ms": value_ms, "ref": ref or False,
        })


class CatalogMetric(models.Model):
    _name = "catalog.metric"
    _description = "Métrica del Motor de Catálogo"
    _order = "id desc"

    run_id = fields.Many2one("catalog.run", required=True, ondelete="cascade", index=True)
    backend_id = fields.Many2one(related="run_id.backend_id", store=True, index=True)
    name = fields.Char(required=True, index=True,
                       help="api_call | normalize | cache | promotion | sync")
    value_ms = fields.Float(string="Valor (ms)")
    ref = fields.Char(string="Referencia")
    create_date = fields.Datetime(index=True)

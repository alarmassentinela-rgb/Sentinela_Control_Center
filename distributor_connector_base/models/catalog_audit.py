"""Auditoría (R5): catalog.audit.log — append-only. Qué cambió, cuándo, qué
proveedor lo reportó, qué usuario/proceso lo hizo, valor anterior/nuevo.
"""
from __future__ import annotations

from odoo import api, fields, models
from odoo.exceptions import UserError


class CatalogAuditLog(models.Model):
    _name = "catalog.audit.log"
    _description = "Bitácora de auditoría del Motor de Catálogo"
    _order = "id desc"

    backend_id = fields.Many2one("distributor.backend", ondelete="set null", index=True)
    run_id = fields.Many2one("catalog.run", ondelete="set null", index=True)
    action = fields.Selection(
        [("discover", "Descubierto"), ("promote", "Promovido"), ("price", "Precio"),
         ("stock", "Stock"), ("sync", "Sincronización"), ("config", "Configuración"),
         ("other", "Otro")], default="other", required=True, index=True)
    model = fields.Char(index=True)
    res_ref = fields.Char(string="Referencia", index=True)
    field_name = fields.Char()
    old_value = fields.Char()
    new_value = fields.Char()
    source = fields.Selection(
        [("cron", "Cron"), ("api", "API"), ("wizard", "Asistente"), ("user", "Usuario"),
         ("system", "Sistema")], default="system")
    user_id = fields.Many2one("res.users", default=lambda s: s.env.user, index=True)
    create_date = fields.Datetime(index=True)
    message = fields.Char()

    @api.model
    def record(self, action, backend_id=None, run_id=None, model=None, res_ref=None,
               field_name=None, old_value=None, new_value=None, source="system", message=None):
        """API de registro de auditoría (usada por el motor/conectores)."""
        return self.sudo().create({
            "action": action, "backend_id": backend_id, "run_id": run_id, "model": model,
            "res_ref": res_ref, "field_name": field_name,
            "old_value": None if old_value is None else str(old_value)[:512],
            "new_value": None if new_value is None else str(new_value)[:512],
            "source": source, "message": message,
        })

    def write(self, vals):
        raise UserError("La bitácora de auditoría es de solo lectura (append-only).")

    def unlink(self):
        if not self.env.is_superuser():
            raise UserError("La bitácora de auditoría no se puede eliminar.")
        return super().unlink()

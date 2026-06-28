"""Extensión del backend para la promoción: asegurar el partner-proveedor."""
from __future__ import annotations

from odoo import models


class DistributorBackend(models.Model):
    _inherit = "distributor.backend"

    def _ensure_partner(self):
        """Devuelve el partner-proveedor del backend; lo crea si falta (para supplierinfo)."""
        self.ensure_one()
        if not self.partner_id:
            P = self.env["res.partner"]
            vals = {"name": self.name or self.connector_key or "Distribuidor"}
            if "supplier_rank" in P._fields:
                vals["supplier_rank"] = 1
            if "autopost_bills" in P._fields:
                vals.setdefault("autopost_bills", "never")
            self.partner_id = P.create(vals)
        return self.partner_id

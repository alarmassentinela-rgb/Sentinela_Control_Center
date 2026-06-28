"""Extensión de `product.supplierinfo` (NATIVO) — regla #6: aprovechar el modelo nativo
producto↔proveedor, no reinventarlo. Aquí viven los datos PROPIEDAD DEL PROVEEDOR
(costo nativo `price`, código nativo `product_code`, plazo nativo `delay`) + extras.
"""
from __future__ import annotations

from odoo import fields, models


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    distributor_backend_id = fields.Many2one(
        "distributor.backend", index=True, ondelete="set null", string="Distribuidor (Motor)")
    distributor_product_id = fields.Char(index=True, string="Distributor Product ID")
    catalog_item_id = fields.Many2one(
        "distributor.catalog.item", index=True, ondelete="set null", string="Ítem de índice")
    warranty = fields.Char(string="Garantía (proveedor)")
    datasheet_url = fields.Char(string="Ficha técnica (URL)")
    last_sync = fields.Datetime(string="Última sincronización")

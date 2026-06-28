"""Producto Maestro (product.template) — fuente de verdad del ERP (reglas #1, #8).

Una vez promovido, el producto es un ACTIVO del ERP: existe con independencia del
distribuidor que lo originó (aunque el distribuidor lo elimine). Los productos PROPIOS
de Alarmas Sentinela quedan con `is_catalog_managed=False` y el Motor NUNCA los toca.
"""
from __future__ import annotations

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_catalog_managed = fields.Boolean(
        string="Gestionado por Motor de Catálogo", default=False, copy=False, index=True,
        help="True = producto nacido/ligado a un distribuidor vía el Motor de Catálogo. "
             "Los productos PROPIOS quedan en False y el Motor de Catálogo NUNCA los modifica.")
    catalog_item_ids = fields.One2many(
        "distributor.catalog.item", "product_tmpl_id", string="Ítems de índice (distribuidores)")
    catalog_item_count = fields.Integer(compute="_compute_catalog_item_count")
    distributor_count = fields.Integer(
        compute="_compute_distributor_count", string="Nº de distribuidores")

    def _compute_catalog_item_count(self):
        for t in self:
            t.catalog_item_count = len(t.catalog_item_ids)

    @api.depends("seller_ids.distributor_backend_id")
    def _compute_distributor_count(self):
        for t in self:
            t.distributor_count = len(t.seller_ids.filtered("distributor_backend_id").mapped("distributor_backend_id"))

"""Política de OWNERSHIP de datos del Producto Maestro (regla #4 de D3b).

Define SIN AMBIGÜEDAD quién es propietario de cada dato. La promoción solo escribe
en el maestro lo que la política permite, y NUNCA pisa lo que es del ERP ni lo que el
usuario editó a mano (campos MIXTOS).

  PROVEEDOR  → viven en product.supplierinfo / distributor.catalog.item (NO en el maestro).
  ERP        → el proveedor NUNCA los escribe.
  MIXTO      → el proveedor los pone al promover y respeta ediciones manuales (snapshot).
"""
from __future__ import annotations

# Datos del PROVEEDOR (no se guardan en product.template; viven en supplierinfo/índice).
PROVIDER_OWNED = [
    "cost",            # supplierinfo.price
    "stock",           # indicativo en catalog.item / autoritativo on-demand
    "warranty",        # supplierinfo.warranty
    "documents",       # supplierinfo.datasheet_url / catalog.item refs (URL)
    "datasheet",
    "distributor_code",  # supplierinfo.product_code / distributor_product_id
    "lead_time",       # supplierinfo.delay
]

# Datos del ERP (el proveedor NUNCA los toca).
ERP_OWNED = [
    "categ_id",                 # categoría comercial
    "taxes_id", "supplier_taxes_id",
    "list_price",               # precio de venta
    "margin",                   # regla de margen (D-futuro)
    "internal_notes",
    "sale_rules",
    "accessory_product_ids", "alternative_product_ids", "optional_product_ids",  # relacionados propios
    "default_code",             # referencia interna (se SIEMBRA al crear, luego es del ERP)
]

# Datos MIXTOS: el proveedor los pone al promover, pero respeta ediciones manuales.
# (template_field, catalog_field) — fuente en el índice/normalizado.
MASTER_MIXED_FIELDS = [
    ("name", "name"),
    ("description_sale", "description"),
]
# 'image' y 'attributes' también son MIXTOS conceptualmente; su poblado (URL→binario /
# product.attribute) se hará en enriquecimiento posterior con la MISMA regla de respeto manual.
MIXED_NOTE = "image, attributes (poblado posterior, misma regla de respeto manual)"

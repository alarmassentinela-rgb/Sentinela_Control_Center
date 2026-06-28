"""Calidad de datos (PURO): detecta problemas y devuelve ADVERTENCIAS sin detener
la sincronización (objetivo #6). Códigos estables para poder filtrar/reportar.
"""
from __future__ import annotations

from typing import List

from odoo.addons.distributor_connector_base.lib.dto import NormalizedProduct

# Códigos de advertencia estables (para métricas/reportes/automatizaciones)
W_MISSING_SAT = "missing_sat_key"
W_EMPTY_CATEGORY = "empty_category"
W_NO_BRAND = "no_brand"
W_BROKEN_IMAGE = "broken_image_url"
W_INVALID_SKU = "invalid_sku"
W_NO_PRICE = "no_price"
W_NEGATIVE_PRICE = "negative_price"


def _looks_like_url(value) -> bool:
    return isinstance(value, str) and value.lower().startswith(("http://", "https://"))


def check(np: NormalizedProduct) -> List[str]:
    """Lista de códigos de advertencia para un NormalizedProduct (vacía = sin problemas)."""
    warns: List[str] = []
    if not np.sat_key:
        warns.append(W_MISSING_SAT)
    if not np.category_path:
        warns.append(W_EMPTY_CATEGORY)
    if not np.brand:
        warns.append(W_NO_BRAND)
    if any(not _looks_like_url(u) for u in np.images):
        warns.append(W_BROKEN_IMAGE)
    if not np.external_ref or not str(np.external_ref).strip():
        warns.append(W_INVALID_SKU)
    if np.price.cost is None and np.price.list is None:
        warns.append(W_NO_PRICE)
    if any(v is not None and v < 0 for v in (np.price.cost, np.price.list, np.price.map, np.price.special)):
        warns.append(W_NEGATIVE_PRICE)
    return warns


def find_duplicates(products: List[NormalizedProduct]) -> List[str]:
    """external_ref repetidos en un lote (detección de duplicados)."""
    seen, dups = set(), set()
    for p in products:
        if p.external_ref in seen:
            dups.add(p.external_ref)
        seen.add(p.external_ref)
    return sorted(dups)

"""Búsqueda del índice (principio #4): por SKU, fabricante, marca, descripción,
keywords, categoría, código SAT y código de barras; insensible a separadores
(code_norm). Preparada para añadir búsqueda semántica (ai_embedding) sin rediseño.
"""
from __future__ import annotations

import re
from typing import List

_NON_ALNUM = re.compile(r"[^a-z0-9]+")

# Estrategia de búsqueda escalable (cada cláusula va por índice a 1M+ filas):
#  - TEXTO → `ilike` respaldado por GIN/trgm (palabras, parciales).
#  - CÓDIGO → igualdad exacta `=` (btree, instantáneo); los parciales de SKU/modelo
#    se cubren con `code_norm` (trgm), que concatena los códigos sin separadores.
TRGM_FIELDS: List[str] = ["name", "keywords", "description", "brand", "manufacturer", "category_path"]
EXACT_FIELDS: List[str] = ["barcode", "sat_code", "distributor_sku", "manufacturer_sku", "distributor_product_id"]
# Compat: campos "buscables" (texto + código).
SEARCH_FIELDS: List[str] = TRGM_FIELDS + EXACT_FIELDS


def normalize_code(value: str) -> str:
    """'PRO-CAT-5E' → 'procat5e' (búsqueda insensible a guiones/espacios)."""
    return _NON_ALNUM.sub("", (value or "").lower())


def build_search_domain(query: str) -> list:
    """Domain Odoo: OR de `query` sobre campos de texto (trgm `ilike`), `code_norm`
    (parcial sin separadores) y campos de código (igualdad exacta). Todo por índice.
    Vacío si la consulta está vacía."""
    q = (query or "").strip()
    if not q:
        return []
    terms = [(f, "ilike", q) for f in TRGM_FIELDS]
    norm = normalize_code(q)
    if norm:
        terms.append(("code_norm", "ilike", norm))
    terms += [(f, "=", q) for f in EXACT_FIELDS]
    # notación polaca: (n-1) operadores '|' antes de n términos
    return ["|"] * (len(terms) - 1) + terms


def build_search_sql(query: str):
    """(where_sql, params) para una consulta SIN `ORDER BY` (BitmapOr + LIMIT en el caller).
    Los nombres de campo provienen de listas blancas fijas (sin inyección); los VALORES van
    parametrizados (%s). Evita el plan 'index-scan ordenado + filter' que escanea todo a 1M."""
    q = (query or "").strip()
    if not q:
        return "", []
    clauses, params = [], []
    like = "%" + q + "%"
    for f in TRGM_FIELDS:            # texto → trgm
        clauses.append("%s ILIKE %%s" % f)
        params.append(like)
    norm = normalize_code(q)
    if norm:                         # parcial de código sin separadores → code_norm trgm
        clauses.append("code_norm ILIKE %s")
        params.append("%" + norm + "%")
    for f in EXACT_FIELDS:           # código → igualdad exacta (btree)
        clauses.append("%s = %%s" % f)
        params.append(q)
    return " OR ".join(clauses), params

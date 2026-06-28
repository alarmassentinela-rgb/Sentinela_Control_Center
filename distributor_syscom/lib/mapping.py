"""Mapeo de normalización Syscom → NormalizedProduct (PURO, sin Odoo ni red).

Es el corazón del conector de referencia y la base de las pruebas con fixtures.
Tolerante a nulos y **compatible hacia adelante**: los campos que Syscom agregue en
el futuro se registran en `raw['_unknown_keys']` y NO rompen la normalización.

Mapa de campos: ver MAPEO_NORMALIZACION.md.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from odoo.addons.distributor_connector_base.lib.dto import (
    NormalizedProduct, NormalizedPrice, NormalizedStock, NormalizedDocument)
from odoo.addons.distributor_connector_base.lib.exceptions import NormalizationError

BACKEND_KEY = "syscom"

# Claves conocidas del detalle /productos/{id}. Lo que NO esté aquí = campo nuevo.
KNOWN_KEYS = frozenset({
    "producto_id", "titulo", "modelo", "marca", "marca_logo", "descripcion",
    "categorias", "categorias_producto_todas", "precios", "existencia",
    "total_existencia", "imagenes", "imagen_360", "img_portada", "iconos",
    "recursos", "sat_key", "sat_description", "unidad_de_medida", "garantia",
    "peso", "alto", "ancho", "largo", "pvol", "link", "link_privado",
    "caracteristicas",
})


def _attributes(raw: Dict) -> List[str]:
    caracs = raw.get("caracteristicas") or []
    if isinstance(caracs, list):
        return [str(c) for c in caracs if c]
    return []


def _to_float(value: Any) -> Optional[float]:
    """'142.38' / 142.38 / '' / None → float | None (nunca lanza)."""
    if value in (None, "", False):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _category_path(raw: Dict) -> List[str]:
    cats = raw.get("categorias") or []
    if not isinstance(cats, list):
        return []
    ordered = sorted(
        (c for c in cats if isinstance(c, dict)),
        key=lambda c: _to_int(c.get("nivel"), 0))
    return [str(c.get("nombre")) for c in ordered if c.get("nombre")]


def _images(raw: Dict) -> List[str]:
    out = []
    imgs = raw.get("imagenes") or []
    if isinstance(imgs, list):
        for it in sorted((i for i in imgs if isinstance(i, dict)),
                         key=lambda i: _to_int(i.get("orden"), 0)):
            url = it.get("imagen")
            if url:
                out.append(url)
    if not out and raw.get("img_portada"):
        out.append(raw["img_portada"])
    return out


def _documents(raw: Dict) -> List[NormalizedDocument]:
    out = []
    for r in (raw.get("recursos") or []):
        if not isinstance(r, dict):
            continue
        path = r.get("path")
        if not path:
            continue
        rec_name = (r.get("recurso") or "documento")
        kind = "datasheet" if "ficha" in rec_name.lower() or "spec" in rec_name.lower() else "other"
        out.append(NormalizedDocument(name=rec_name, url=path, kind=kind))
    return out


def _price(raw: Dict) -> NormalizedPrice:
    p = raw.get("precios") or {}
    if not isinstance(p, dict):
        p = {}
    return NormalizedPrice(
        cost=_to_float(p.get("precio_descuento")),
        list=_to_float(p.get("precio_lista")) or _to_float(p.get("precio_1")),
        map=_to_float(p.get("precio_map")),
        special=_to_float(p.get("precio_especial")),
        currency="USD",  # Syscom cotiza en USD
    )


def _stock(raw: Dict) -> NormalizedStock:
    total = _to_int(raw.get("total_existencia"), -1)
    exist = raw.get("existencia") or {}
    by_wh: Dict[str, int] = {}
    if isinstance(exist, dict):
        if total < 0:
            total = _to_int(exist.get("nuevo"), 0)
        detalle = exist.get("detalle") or []
        if isinstance(detalle, list):
            for d in detalle:
                if isinstance(d, dict):
                    key = str(d.get("sucursal") or d.get("id") or d.get("clave") or len(by_wh))
                    by_wh[key] = _to_int(d.get("cantidad") or d.get("existencia"), 0)
    return NormalizedStock(total=max(0, total), by_warehouse=by_wh)


def _dimensions(raw: Dict) -> Dict[str, float]:
    out = {}
    for src, dst in (("alto", "alto"), ("ancho", "ancho"), ("largo", "largo"), ("pvol", "volumen")):
        v = _to_float(raw.get(src))
        if v is not None:
            out[dst] = v
    return out


def is_error_payload(raw: Dict) -> bool:
    """Syscom devuelve HTTP 200 con {'error': ...} para productos no disponibles."""
    return isinstance(raw, dict) and "error" in raw and "producto_id" not in raw


def unknown_keys(raw: Dict) -> List[str]:
    return sorted(k for k in raw if k not in KNOWN_KEYS and not k.startswith("_"))


def normalize(raw: Dict, backend_key: str = BACKEND_KEY) -> NormalizedProduct:
    """Mapea el JSON de Syscom a NormalizedProduct. Lanza NormalizationError si es
    un payload de error o no trae producto_id."""
    if not isinstance(raw, dict):
        raise NormalizationError("payload no es dict")
    if is_error_payload(raw):
        raise NormalizationError("payload de error Syscom: %s" % raw.get("error"))
    ref = raw.get("producto_id")
    if not ref:
        raise NormalizationError("payload sin producto_id")

    um = raw.get("unidad_de_medida") or {}
    np = NormalizedProduct(
        backend_key=backend_key,
        external_ref=str(ref),
        name=(raw.get("titulo") or raw.get("modelo") or str(ref)),
        brand=raw.get("marca") or None,
        model=raw.get("modelo") or None,
        description=raw.get("descripcion") or None,
        attributes=_attributes(raw),
        category_path=_category_path(raw),
        price=_price(raw),
        stock=_stock(raw),
        images=_images(raw),
        image_360=raw.get("imagen_360") or None,
        documents=_documents(raw),
        sat_key=str(raw["sat_key"]) if raw.get("sat_key") else None,
        sat_unit=(um.get("clave_unidad_sat") if isinstance(um, dict) else None) or None,
        warranty=raw.get("garantia") or None,
        dimensions=_dimensions(raw),
        weight=_to_float(raw.get("peso")),
        raw={"_unknown_keys": unknown_keys(raw), "source": backend_key, "payload": raw},
    )
    return np


def to_embedding_text(np: NormalizedProduct) -> str:
    """Texto canónico para futuros embeddings / búsqueda semántica (objetivo IA).
    No genera el embedding; deja el insumo limpio listo, sin rediseñar el conector."""
    parts = [np.name, np.brand, np.model, " > ".join(np.category_path),
             np.description, " ".join(np.attributes)]
    return " | ".join(p for p in parts if p)

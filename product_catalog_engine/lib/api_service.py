"""Capa de servicios del Motor de Catálogo (transporte-agnóstica).

La consume la interfaz pública REST (D3c) hoy y podrá consumirla GraphQL mañana
(Filosofía §14: no duplicar lógica). Devuelve estructuras serializables (dicts), NO
objetos Odoo. La lógica de negocio vive aquí/en los modelos, NUNCA en el controlador.
"""
from __future__ import annotations

from odoo.addons.distributor_connector_base.lib import version as ver

# Campos públicos del DTO de catálogo (estables; ver Especificación §1/§6).
PUBLIC_SORT_FIELDS = {"name", "brand", "price_list", "stock_total", "sync_tier", "id"}
PUBLIC_FILTERS = {"backend", "brand", "manufacturer", "sat_code", "barcode", "promoted"}


def item_to_dto(item) -> dict:
    """Producto del índice → DTO público (sin binarios; identidades separadas)."""
    return {
        "distributor_product_id": item.distributor_product_id,
        "backend": item.backend_id.connector_key or item.backend_id.name,
        "name": item.name,
        "brand": item.brand or None,
        "manufacturer": item.manufacturer or None,
        "distributor_sku": item.distributor_sku or None,
        "manufacturer_sku": item.manufacturer_sku or None,
        "barcode": item.barcode or None,
        "sat_code": item.sat_code or None,
        "category_path": item.category_path or None,
        "price": {"list": item.price_list or None, "cost": item.price_cost or None,
                  "currency": item.currency_code or "USD"},
        "stock": {"total": item.stock_total},
        "thumb_url": item.thumb_url or None,
        "image_count": item.image_count,
        "doc_count": item.doc_count,
        "freshness": {
            "status": item.freshness_status,
            "price_expires_at": _dt(item.price_expires_at),
            "stock_expires_at": _dt(item.stock_expires_at),
            "enrichment_expires_at": _dt(item.enrichment_expires_at),
        },
        "product_master_id": item.product_tmpl_id.id or None,
        "is_promoted": bool(item.product_tmpl_id),
    }


def _dt(value):
    return value.isoformat() if value else None


class CatalogApiService:
    """Servicio del catálogo. Recibe `env` (sudo recomendado tras autenticar)."""

    def __init__(self, env):
        self.env = env
        self.Item = env["distributor.catalog.item"]

    # ----- búsqueda con filtros / orden / paginación -----
    def search(self, q=None, filters=None, page=1, page_size=50, sort="id"):
        filters = filters or {}
        page = max(1, int(page or 1))
        page_size = min(200, max(1, int(page_size or 50)))
        domain = self._filters_to_domain(filters)
        if q:
            ids = self.Item.search_index(q, limit=2000).ids   # candidatos por índice (2 fases)
            domain = [("id", "in", ids)] + domain
        order = self._sort_to_order(sort)
        total = self.Item.search_count(domain)
        recs = self.Item.search(domain, order=order, limit=page_size, offset=(page - 1) * page_size)
        return {
            "data": [item_to_dto(r) for r in recs],
            "pagination": {"page": page, "page_size": page_size, "total": total,
                           "pages": (total + page_size - 1) // page_size},
        }

    def _filters_to_domain(self, filters):
        dom = []
        if filters.get("backend"):
            dom.append(("backend_id.connector_key", "=", filters["backend"]))
        if filters.get("brand"):
            dom.append(("brand", "ilike", filters["brand"]))
        if filters.get("manufacturer"):
            dom.append(("manufacturer", "ilike", filters["manufacturer"]))
        if filters.get("sat_code"):
            dom.append(("sat_code", "=", filters["sat_code"]))
        if filters.get("barcode"):
            dom.append(("barcode", "=", filters["barcode"]))
        if filters.get("promoted") in ("1", "true", True):
            dom.append(("product_tmpl_id", "!=", False))
        return dom

    def _sort_to_order(self, sort):
        sort = (sort or "id").strip()
        desc = sort.startswith("-")
        field = sort[1:] if desc else sort
        if field not in PUBLIC_SORT_FIELDS:
            field = "id"
        return "%s %s" % (field, "desc" if desc else "asc")

    # ----- detalle (refresca on-demand si está vencido) -----
    def get_product(self, ref, backend=None, refresh_if_stale=True):
        item = self._find(ref, backend)
        if not item:
            return None
        item.register_hit()
        if refresh_if_stale and item.freshness_status == "expired":
            try:
                item.refresh(source="api")
            except Exception:  # noqa: BLE001 - si la API del proveedor falla, servimos lo cacheado
                pass
        return item_to_dto(item)

    def promote(self, ref, backend=None):
        item = self._find(ref, backend)
        if not item:
            return None
        master = item.promote(source="api")
        return {"distributor_product_id": ref, "product_master_id": master.id,
                "name": master.name, "is_catalog_managed": master.is_catalog_managed,
                "distributors": master.distributor_count}

    def _find(self, ref, backend=None):
        dom = [("distributor_product_id", "=", ref)]
        if backend:
            dom.append(("backend_id.connector_key", "=", backend))
        return self.Item.search(dom, limit=1)

    # ----- salud / métricas -----
    def health(self):
        return {"status": "ok", "engine_version": ver.ENGINE_VERSION,
                "items": self.Item.search_count([]),
                "backends": self.env["distributor.backend"].search_count([("active", "=", True)])}

    def metrics(self):
        return self.env["catalog.dashboard"]._collect()

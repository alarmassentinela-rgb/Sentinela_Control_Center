"""distributor.catalog.item — ÍNDICE de búsqueda del Motor de Catálogo.

IMPORTANTE (arquitectura):
  * Esto es SOLO un índice de búsqueda ligero. NO es el producto maestro, NO es
    inventario, NO son precios definitivos, NO es el producto de Odoo.
  * El producto maestro es `product.template` (vía `product_tmpl_id` cuando se promueve).
  * Sin binarios: solo metadatos y REFERENCIAS (URLs/contadores).

Diseñado para >1,000,000 de registros: identidad única, índices btree + GIN/trgm,
campos reservados para IA, y caché por TTL desacoplado (ver lib/cache.py).
"""
from __future__ import annotations

import logging
import re
import time

from odoo import api, fields, models

from ..lib import search as search_lib

_logger = logging.getLogger(__name__)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


class DistributorCatalogItem(models.Model):
    _name = "distributor.catalog.item"
    _description = "Índice de catálogo de distribuidor (búsqueda ligera, NO es el producto maestro)"
    _order = "name"
    # _rec_name = name (default)

    # ------------------------------------------------------------------
    # IDENTIDAD (principio #3): claves separadas; el SKU del distribuidor
    # NUNCA es la identidad del producto.
    # ------------------------------------------------------------------
    backend_id = fields.Many2one(
        "distributor.backend", required=True, ondelete="cascade", index=True,
        string="Distribuidor")
    distributor_product_id = fields.Char(
        required=True, index=True, string="Distributor Product ID",
        help="ID interno del producto en el distribuidor (identidad dentro del distribuidor).")
    distributor_sku = fields.Char(index=True, string="Distributor SKU")
    manufacturer_sku = fields.Char(index=True, string="Manufacturer SKU")
    barcode = fields.Char(index=True, string="Barcode")
    sat_code = fields.Char(index=True, string="SAT Code")
    product_tmpl_id = fields.Many2one(
        "product.template", index=True, ondelete="set null", copy=False,
        string="Product Master (Odoo)",
        help="Producto maestro de Odoo cuando el ítem fue PROMOVIDO (D3b). "
             "Vacío = aún no promovido; el índice NO es el producto maestro.")
    code_norm = fields.Char(
        compute="_compute_code_norm", store=True, index=True, string="Código normalizado",
        help="SKU/modelo sin guiones/espacios (búsqueda insensible a separadores: pro-cat-5e ↔ procat5e).")

    # ------------------------------------------------------------------
    # METADATOS DE BÚSQUEDA (principio #4)
    # ------------------------------------------------------------------
    name = fields.Char(required=True, index=True)
    brand = fields.Char(index=True)
    manufacturer = fields.Char(index=True, string="Fabricante")
    category_path = fields.Char(string="Categoría")
    keywords = fields.Text(help="Palabras clave para búsqueda (trgm).")
    description = fields.Text(help="Descripción corta en texto (sin HTML/binarios).")
    # Columna ÚNICA de búsqueda difusa (escala): concatena texto + códigos. Un solo índice
    # GIN/trgm sobre esta columna evita el OR multi-campo (que a 1M provoca Seq Scan).
    search_blob = fields.Text(compute="_compute_search_blob", store=True, copy=False)

    # ------------------------------------------------------------------
    # SNAPSHOT INDICATIVO (principio #1: NO son precios/inventario definitivos)
    # ------------------------------------------------------------------
    price_list = fields.Float(string="Precio lista (indicativo)")
    price_cost = fields.Float(string="Costo (indicativo)")
    currency_code = fields.Char(default="USD", string="Moneda")
    stock_total = fields.Integer(string="Stock (indicativo)")
    snapshot_at = fields.Datetime(string="Snapshot al")

    # ------------------------------------------------------------------
    # REFERENCIAS (principio #2: sin binarios — solo URLs/contadores)
    # ------------------------------------------------------------------
    thumb_url = fields.Char(string="Miniatura (URL)")
    image_count = fields.Integer()
    doc_count = fields.Integer()

    # ------------------------------------------------------------------
    # CACHÉ / TTL (la caché reemplazable vive en lib/cache.py; aquí el snapshot crudo)
    # ------------------------------------------------------------------
    raw_cache = fields.Text(string="Caché normalizada (JSON)", copy=False)
    fetched_price_at = fields.Datetime(copy=False)
    fetched_stock_at = fields.Datetime(copy=False)
    fetched_enrichment_at = fields.Datetime(copy=False)

    # ------------------------------------------------------------------
    # RESERVADO PARA IA (principio #7): no se llena hoy, pero el modelo ya lo prevé.
    # Objetivo de embeddings: pgvector (ver ESTRATEGIA_INDICES_CACHE.md).
    # ------------------------------------------------------------------
    ai_keywords = fields.Text(string="Keywords IA (reservado)")
    ai_category = fields.Char(string="Clasificación IA (reservado)")
    ai_embedding = fields.Text(string="Embedding (reservado)", copy=False,
                               help="Reservado; destino futuro: columna pgvector.")
    ai_embedding_model = fields.Char(string="Modelo de embedding (reservado)")
    ai_indexed_at = fields.Datetime(string="Indexado IA (reservado)")

    # ------------------------------------------------------------------
    # Operación
    # ------------------------------------------------------------------
    sync_tier = fields.Selection(
        [("0", "Caliente"), ("1", "Activo"), ("2", "Inactivo"), ("3", "Catálogo")],
        default="3", index=True, string="Prioridad")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("backend_extref_uniq", "unique(backend_id, distributor_product_id)",
         "Ya existe un ítem de índice para ese distribuidor + Distributor Product ID."),
    ]

    @api.depends("distributor_sku", "manufacturer_sku", "distributor_product_id")
    def _compute_code_norm(self):
        for r in self:
            raw = " ".join(filter(None, [r.distributor_sku, r.manufacturer_sku, r.distributor_product_id]))
            r.code_norm = _NON_ALNUM.sub("", (raw or "").lower())

    @api.depends("name", "brand", "manufacturer", "keywords", "description", "category_path",
                 "distributor_sku", "manufacturer_sku", "barcode", "sat_code", "code_norm")
    def _compute_search_blob(self):
        for r in self:
            parts = [r.name, r.brand, r.manufacturer, r.keywords, r.description, r.category_path,
                     r.distributor_sku, r.manufacturer_sku, r.barcode, r.sat_code, r.code_norm]
            r.search_blob = " ".join(p for p in parts if p).lower()

    # ------------------------------------------------------------------
    # Índices SQL para escala (principio #5): GIN/trgm para búsqueda difusa.
    # btree ya se crean por index=True. trgm requiere pg_trgm.
    # ------------------------------------------------------------------
    def init(self):
        cr = self.env.cr
        try:
            cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        except Exception as e:  # noqa: BLE001 - sin permisos: btree sigue, trgm se omite
            _logger.warning("pg_trgm no disponible (%s); búsqueda difusa usará btree/seq", e)
            cr.rollback()
            return
        # Índice de búsqueda difusa: UNA columna (search_blob) + code_norm + name.
        for col in ("search_blob", "code_norm", "name"):
            cr.execute(
                "CREATE INDEX IF NOT EXISTS %s_%s_trgm ON %s USING gin (%s gin_trgm_ops)"
                % (self._table, col, self._table, col))
        # Limpia los trgm por-campo reemplazados por search_blob (ahorra disco a 1M).
        for col in ("keywords", "description", "brand", "manufacturer", "category_path"):
            cr.execute("DROP INDEX IF EXISTS %s_%s_trgm" % (self._table, col))

    # ------------------------------------------------------------------
    # Promoción → producto maestro (la lógica completa es D3b; aquí el gancho + AUDITORÍA #8)
    # ------------------------------------------------------------------
    def link_master(self, product_tmpl, source="system"):
        """Liga el ítem de índice a un producto maestro de Odoo y AUDITA (diseño #8).
        La promoción completa (crear product.template + supplierinfo) llega en D3b."""
        self.ensure_one()
        old = self.product_tmpl_id.id
        self.product_tmpl_id = product_tmpl.id
        self.env["catalog.audit.log"].sudo().record(
            action="promote", backend_id=self.backend_id.id,
            model="distributor.catalog.item", res_ref=self.distributor_product_id,
            field_name="product_tmpl_id", old_value=old, new_value=product_tmpl.id,
            source=source, message="Índice ligado a producto maestro")
        return True

    # ------------------------------------------------------------------
    # Búsqueda (principio #4) + medición de tiempo (principio #9)
    # ------------------------------------------------------------------
    def _run_search_sql(self, where, params, limit, backend_id=None, exclude_ids=None):
        sql = "SELECT id FROM %s WHERE active AND (%s)" % (self._table, where)
        params = list(params)
        if backend_id:
            sql += " AND backend_id = %s"
            params.append(backend_id)
        if exclude_ids:
            sql += " AND id <> ALL(%s)"
            params.append(list(exclude_ids))
        sql += " LIMIT %s"
        params.append(limit)
        self.env.cr.execute(sql, params)
        return [r[0] for r in self.env.cr.fetchall()]

    @api.model
    def search_index(self, query, limit=80, backend_id=None):
        """Busca en el índice por SKU/fabricante/marca/descripción/keywords/categoría/
        SAT/barcode (+ código normalizado). Devuelve un recordset.

        Escala (principio #10) — búsqueda en DOS FASES para que SIEMPRE use índice:
          1) IGUALDAD EXACTA de código (barcode/SAT/SKU/modelo/product_id/code_norm) →
             btree, instantáneo incluso si el término es muy selectivo (1 entre 1M).
          2) Solo si faltan resultados: TEXTO por trgm (nombre/marca/keywords/…).
        Evita el Seq Scan que provoca el OR mixto (btree+GIN) con LIMIT por mala
        estimación de selectividad. Sin `ORDER BY`; el re-ranking lo hace el consumidor."""
        q = (query or "").strip()
        if not q:
            return self.browse()
        # La búsqueda usa SQL crudo (índices); aseguramos que lo pendiente en cache ORM
        # (p. ej. search_blob/code_norm recién calculados) esté escrito en la BD.
        self.flush_model()
        norm = search_lib.normalize_code(q)

        # Fase 1 — código exacto (btree)
        ex_clauses = ["%s = %%s" % f for f in search_lib.EXACT_FIELDS]
        ex_params = [q] * len(search_lib.EXACT_FIELDS)
        if norm:
            ex_clauses.append("code_norm = %s")
            ex_params.append(norm)
        ids = self._run_search_sql(" OR ".join(ex_clauses), ex_params, limit, backend_id)
        if ids:
            # Coincidencia exacta de código = respuesta precisa; no se mezcla con texto difuso.
            return self.browse(ids)

        # Fase 2 — texto difuso: UN solo escaneo trgm sobre search_blob (escala).
        more = self._run_search_sql("search_blob ILIKE %s", ["%" + q.lower() + "%"],
                                    limit, backend_id)
        return self.browse(more)

    @api.model
    def search_index_timed(self, query, limit=80, backend_id=None):
        """Igual que search_index pero devuelve (recordset, ms) para benchmark/métricas."""
        t0 = time.perf_counter()
        recs = self.search_index(query, limit=limit, backend_id=backend_id)
        return recs, round((time.perf_counter() - t0) * 1000.0, 3)

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        if name and operator in ("ilike", "=ilike", "like"):
            recs = self.search_index(name, limit=limit or 100)
            if args:
                recs = recs.filtered_domain(args)
            return [(r.id, r.display_name) for r in recs]
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

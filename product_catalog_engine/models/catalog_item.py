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

import json
import logging
import re
import time

from odoo import api, fields, models

from ..lib import ownership
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
    provider_snapshot = fields.Text(
        string="Snapshot de campos del proveedor (JSON)", copy=False,
        help="Últimos valores que el proveedor empujó a los campos MIXTOS del maestro; "
             "permite detectar ediciones manuales y respetarlas (no sobrescribir).")
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

    # ==================================================================
    # PROMOCIÓN índice → Producto Maestro (D3b). Idempotente, respeta lo
    # manual, multi-proveedor. Ver D3B_*.md y lib/ownership.py.
    # ==================================================================
    def promote(self, source="user"):
        """Promueve los ítems a Producto Maestro (idempotente). Devuelve los maestros."""
        masters = self.env["product.template"]
        for item in self:
            masters |= item._promote_one(source=source)
        return masters

    def _promote_one(self, source="user"):
        self.ensure_one()
        tmpl = self._find_or_create_master()
        self._sync_supplierinfo(tmpl, source=source)        # datos del PROVEEDOR
        self._sync_mixed_fields(tmpl, source=source)         # MIXTOS, respeta manual
        if self.product_tmpl_id != tmpl:
            self.link_master(tmpl, source=source)            # enlaza + audita
        self.fetched_enrichment_at = fields.Datetime.now()
        return tmpl

    def _find_or_create_master(self):
        """Idempotente + anti-duplicado + multi-proveedor (#2, #7). NUNCA toca productos
        propios: el match exige `is_catalog_managed=True`."""
        self.ensure_one()
        Tmpl = self.env["product.template"]
        if self.product_tmpl_id:
            return self.product_tmpl_id
        # 1) ya promovido por ESTE distribuidor
        si = self.env["product.supplierinfo"].search([
            ("distributor_backend_id", "=", self.backend_id.id),
            ("distributor_product_id", "=", self.distributor_product_id)], limit=1)
        if si.product_tmpl_id:
            return si.product_tmpl_id
        # 2) cross-distribuidor por código de barras (solo maestros gestionados)
        if self.barcode:
            t = Tmpl.search([("barcode", "=", self.barcode), ("is_catalog_managed", "=", True)], limit=1)
            if t:
                return t
        # 3) por referencia de fabricante (solo gestionados → nunca pisa propios)
        if self.manufacturer_sku:
            t = Tmpl.search([("default_code", "=", self.manufacturer_sku), ("is_catalog_managed", "=", True)], limit=1)
            if t:
                return t
        # 4) nace el Producto Maestro (activo del ERP)
        return Tmpl.create(self._master_create_vals())

    def _master_create_vals(self):
        self.ensure_one()
        Tmpl = self.env["product.template"]
        # barcode es ÚNICO en Odoo: solo se copia si está libre (si ya lo tiene otro producto
        # —p. ej. uno PROPIO— no se copia, para no colisionar ni secuestrarlo).
        barcode = self.barcode or False
        if barcode and Tmpl.search_count([("barcode", "=", barcode)]):
            barcode = False
        vals = {
            "name": self.name,
            "default_code": self.manufacturer_sku or self.distributor_sku or False,
            "barcode": barcode,
            "type": "consu",
            "is_catalog_managed": True,
            "description_sale": self.description or False,
        }
        if self.sat_code and "l10n_mx_edi_code_sat" in Tmpl._fields:
            vals["l10n_mx_edi_code_sat"] = self.sat_code
        for warn in ("sale_line_warn", "purchase_line_warn"):
            if warn in Tmpl._fields:
                vals[warn] = "no-message"
        return vals

    def _sync_supplierinfo(self, tmpl, source="user"):
        """Crea/actualiza el product.supplierinfo (NATIVO) con datos del PROVEEDOR (#6)."""
        self.ensure_one()
        partner = self.backend_id._ensure_partner()
        SI = self.env["product.supplierinfo"]
        si = SI.search([
            ("distributor_backend_id", "=", self.backend_id.id),
            ("distributor_product_id", "=", self.distributor_product_id),
            ("product_tmpl_id", "=", tmpl.id)], limit=1)
        vals = {
            "partner_id": partner.id,
            "product_tmpl_id": tmpl.id,
            "product_code": self.distributor_sku or self.distributor_product_id,
            "price": self.price_cost or 0.0,
            "distributor_backend_id": self.backend_id.id,
            "distributor_product_id": self.distributor_product_id,
            "catalog_item_id": self.id,
            "last_sync": fields.Datetime.now(),
        }
        if si:
            old_price = si.price
            si.write(vals)
            if old_price != si.price:
                self.env["catalog.audit.log"].record(
                    action="price", backend_id=self.backend_id.id, model="product.supplierinfo",
                    res_ref=self.distributor_product_id, field_name="price",
                    old_value=old_price, new_value=si.price, source=source)
        else:
            SI.create(vals)
            self.env["catalog.audit.log"].record(
                action="sync", backend_id=self.backend_id.id, model="product.supplierinfo",
                res_ref=self.distributor_product_id, field_name="create",
                old_value=None, new_value=tmpl.id, source=source)
        return si

    def _sync_mixed_fields(self, tmpl, source="user"):
        """Campos MIXTOS: el proveedor los pone, pero RESPETA ediciones manuales (#3).
        Detecta edición manual comparando contra el último valor que el proveedor empujó."""
        self.ensure_one()
        snap = json.loads(self.provider_snapshot) if self.provider_snapshot else {}
        for tfield, cfield in ownership.MASTER_MIXED_FIELDS:
            if tfield not in tmpl._fields:
                continue
            new_val = self[cfield] or False
            cur = tmpl[tfield] or False
            last_provider = snap.get(tfield)
            # aplica solo si está vacío o NO fue editado a mano (cur == último del proveedor)
            if (not cur) or (cur == last_provider):
                if new_val and cur != new_val:
                    self.env["catalog.audit.log"].record(
                        action="sync", backend_id=self.backend_id.id, model="product.template",
                        res_ref=str(tmpl.id), field_name=tfield, old_value=cur,
                        new_value=new_val, source=source)
                    tmpl[tfield] = new_val
            snap[tfield] = new_val
        self.provider_snapshot = json.dumps(snap, ensure_ascii=False, default=str)

    def action_promote(self):
        masters = self.promote(source="user")
        return {
            "type": "ir.actions.client", "tag": "display_notification",
            "params": {"title": "Promoción",
                       "message": "%d producto(s) maestro(s) generado(s)/actualizado(s)." % len(masters),
                       "type": "success", "sticky": False},
        }

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

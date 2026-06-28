# D3a — Índice del Motor de Catálogo: modelo de datos, índices, caché y benchmark

**Fecha:** 28-jun-2026 · Módulo `product_catalog_engine` (Catalog Engine 1.0.0) · **Solo STAGING.**

---

## 1. Principio: el índice NO es el catálogo
`distributor.catalog.item` es **solo un índice de búsqueda ligero**. NO es el producto maestro, NO es inventario, NO son precios definitivos, NO es el producto de Odoo. Solo metadatos + **referencias** (URLs/contadores) para **localizar** rápido. El producto maestro sigue siendo `product.template` (se enlaza por `product_tmpl_id` al promover, en D3b). **Sin binarios** (imágenes/PDF/fichas/videos → solo URL).

## 2. Modelo de datos definitivo (`distributor.catalog.item`)
| Grupo | Campos | Notas |
|---|---|---|
| **Identidad** | `backend_id`, `distributor_product_id`, `distributor_sku`, `manufacturer_sku`, `barcode`, `sat_code`, `code_norm`, `product_tmpl_id` | Identidad del índice = **(backend_id, distributor_product_id)** ÚNICA. El **SKU NO es la identidad**. `product_tmpl_id` = enlace al maestro (Product Master ID), vacío hasta promover. `code_norm` = SKU/modelo sin separadores. |
| **Búsqueda** | `name`, `brand`, `manufacturer`, `category_path`, `keywords`, `description`, **`search_blob`** | `search_blob` (computado, almacenado) concatena texto+códigos → **una sola columna** para búsqueda difusa. |
| **Snapshot indicativo** | `price_list`, `price_cost`, `currency_code`, `stock_total`, `snapshot_at` | **No autoritativo** (el precio/stock real es bajo demanda / `supplierinfo`). |
| **Referencias (sin binarios)** | `thumb_url`, `image_count`, `doc_count` | Solo URL/contadores. |
| **Caché/TTL** | `raw_cache`, `fetched_price_at`, `fetched_stock_at`, `fetched_enrichment_at` | Snapshot crudo + marcas de frescura. |
| **Reservado IA** | `ai_keywords`, `ai_category`, `ai_embedding`, `ai_embedding_model`, `ai_indexed_at` | Previsto; destino de embeddings: **pgvector** (no se modifica el modelo después). |
| **Operación** | `sync_tier` (0/1/2/3), `active` | Prioridad de sync (D3d). |

Identidades separadas (principio #3): **Product Master ID** (`product_tmpl_id`) · **Distributor Product ID** (`distributor_product_id`) · **Distributor SKU** (`distributor_sku`) · **Manufacturer SKU** (`manufacturer_sku`) · **Barcode** (`barcode`) · **SAT Code** (`sat_code`).

## 3. Estrategia de indexación (para 1M+ filas)
- **Único de identidad:** `unique(backend_id, distributor_product_id)`.
- **btree** (igualdad exacta instantánea): `distributor_product_id`, `distributor_sku`, `manufacturer_sku`, `barcode`, `sat_code`, `code_norm`, `brand`, `manufacturer`, `product_tmpl_id`, `sync_tier`, `backend_id`.
- **GIN / pg_trgm** (búsqueda difusa `ILIKE`): **`search_blob`** (columna única), `code_norm`, `name`. Se crean en `init()` (`CREATE EXTENSION IF NOT EXISTS pg_trgm`; guarda si no hay permisos).
- **Búsqueda en 2 fases** (`search_index`), para que SIEMPRE use índice y nunca Seq Scan:
  1. **Igualdad exacta de código** (btree) → respuesta precisa e instantánea aun para 1 entre 1M; si hay match, **regresa** (no mezcla con difuso).
  2. **Texto difuso**: **un solo** `search_blob ILIKE %q%` (GIN/trgm). El OR multi-campo se evitó a propósito: a 1M provoca que el planner haga Seq Scan por mala estimación de selectividad.
- **Sin `ORDER BY` en la búsqueda** (el re-ranking lo hace el consumidor): `ORDER BY … LIMIT` con predicado selectivo hacía que el planner escaneara el índice ordenado hasta hallar la coincidencia.
- ⚠️ **Operativo:** tras una carga/sync masiva hay que **`ANALYZE`** la tabla (estadísticas frescas) para que el planner use los índices; el sync de D3d debe ejecutarlo (o confiar en autovacuum).

## 4. Estrategia de caché (reemplazable — principio #6)
- Interfaz **`CacheBackend`** (`get/set/delete/stats`). El Motor usa la interfaz, **no** una implementación.
- **`PostgresCacheBackend`** (default, modelo `catalog.cache.entry` con TTL) — hoy.
- **`RedisCacheBackend`** (interfaz lista, stub) — mañana, sin tocar el Motor.
- Selección por `ir.config_parameter` `catalog.cache_backend` (postgres|redis). TTL diferenciado por tipo de dato (precio/stock/enriquecimiento), ya previsto en los campos `fetched_*`.

## 5. Benchmark (criterio de aceptación #10) — **1,000,000 de registros en STAGING**
| Caso | Resultado |
|---|---|
| Igualdad barcode (btree, SQL) | **0.04 ms** (Index Scan) |
| Igualdad sat_code (btree, SQL) | **0.37 ms** |
| **Búsqueda ORM — código exacto** (modelo/barcode/SKU/code_norm) | **0.3 ms** |
| **Búsqueda ORM — texto común** ("domo", "HIKVISION") | **1–2 ms** |
| **Búsqueda ORM — texto selectivo** ("benchmark 987654", ~10/1M) | **64 ms** |
| Inserción masiva 1M (con search_blob) | ~113 s (una vez) |
| `ANALYZE` 1M | ~0.34 s |
- **Todas las búsquedas usan índice (sin Seq Scan).** Los datos sintéticos se **eliminaron** tras medir (tabla de vuelta en 0).
- Conclusión: el índice **escala a 1M+** sin afectar el ERP (búsquedas sub-100 ms; los códigos sub-milisegundo).

## 6. Preparación para IA (principio #7)
Campos reservados `ai_*` (keywords, category, embedding, model, indexed_at). El objetivo de embeddings es **pgvector** (columna `vector` + índice IVFFlat/HNSW) — se añadirá sin rediseñar el modelo (los campos ya existen; solo cambia el tipo/almacenamiento del embedding). La búsqueda semántica convivirá con la actual (híbrida léxica+vectorial).

## 7. Auditoría (principio #8)
`distributor.catalog.item.link_master()` ya **audita** (`catalog.audit.log`, action=`promote`) el enlace índice→maestro, aunque la promoción completa llega en D3b. Diseño listo desde D3a.

## 8. Métricas (principio #9)
- **Búsqueda:** `search_index_timed()` devuelve (recordset, ms).
- **Caché:** `CacheBackend.stats()` → hits/misses/ratio.
- **Indexación/sync:** se registran en `catalog.run`/`catalog.metric` (infra del SDK) cuando corra el sync (D3d).

> **Nota de diseño (deuda menor):** agregar un campo computado-almacenado (`search_blob`) a una tabla ya poblada dispara recompute masivo en `-u`. Hoy la tabla nace vacía (sin impacto); a futuro, cambios de campos computados sobre tablas grandes se harán por migración controlada.

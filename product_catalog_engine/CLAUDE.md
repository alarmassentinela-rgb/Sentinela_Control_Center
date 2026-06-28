# product_catalog_engine (Motor de Catálogo)

Núcleo del Motor de Catálogo (Alea Systems). **D3a**: índice de búsqueda + búsqueda escalable + caché reemplazable. Depende de `distributor_connector_base` (SDK) y `product`.

> Estado/decisiones del proyecto: ver `BLUEPRINT_*` / `CATALOG_ENGINE_STANDARDS_*` / `D3A_*` del repo raíz y la memoria [[project-motor-catalogo]]. Solo STAGING; nada en PROD.

## Modelos
- **`distributor.catalog.item`** — ÍNDICE ligero (NO es el producto maestro, NO inventario, NO precios definitivos, sin binarios). Identidad única `(backend_id, distributor_product_id)`; identidades separadas (Product Master/Distributor Product/SKU/Manufacturer SKU/Barcode/SAT). `search_blob` (computado, almacenado) = columna única de búsqueda difusa. Campos `ai_*` reservados (pgvector futuro). `link_master()` audita (D3b hará la promoción completa).
- **`catalog.cache.entry`** — almacén del backend de caché Postgres.

## Búsqueda (clave de escala — leer antes de tocar)
`search_index()` = **2 fases**: (1) igualdad exacta de código (btree) → si hay match, regresa; (2) `search_blob ILIKE %q%` (un solo GIN/trgm). **NO** hacer OR multi-campo (a 1M el planner hace Seq Scan por mala estimación). **NO** poner `ORDER BY` (con LIMIT y predicado selectivo escanea el índice ordenado completo). Usa **SQL crudo** → `self.flush_model()` antes (los campos computados deben estar en BD). Tras carga masiva: **`ANALYZE`** (sin stats frescas, el planner ignora los índices y hace Seq Scan).

## Índices (`init()`)
btree por `index=True` en las columnas de identidad/lookup. GIN/trgm en `search_blob`, `code_norm`, `name` (requiere `pg_trgm`; se crea en `init()`, guarda si no hay permisos). Se eliminan los trgm por-campo viejos (reemplazados por `search_blob`).

## Caché reemplazable
`lib/cache.py`: interfaz `CacheBackend` + `PostgresCacheBackend` (default) + `RedisCacheBackend` (stub). Factoría `get_cache_backend(env)` por `ir.config_parameter` `catalog.cache_backend`. El Motor usa la interfaz, no la implementación.

## Trampas
- Campo computado-almacenado nuevo (`search_blob`) sobre tabla poblada = recompute masivo en `-u`. La tabla nace vacía; a futuro, migración controlada.
- El benchmark inserta/borra datos sintéticos por SQL (`distributor_product_id LIKE 'BPID%'`); siempre limpiar tras medir.

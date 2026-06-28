# product_catalog_engine — Motor de Catálogo (D3a: índice + búsqueda + caché)

Núcleo del Motor de Catálogo. **D3a** entrega el **índice de búsqueda** (`distributor.catalog.item`),
la **búsqueda escalable** (1M+) y la **caché reemplazable**. La promoción a producto maestro,
la API REST y el scheduler llegan en D3b/D3c/D3d.

- Catalog Engine `1.0.0` · módulo Odoo `18.0.1.0.0` · depende de `distributor_connector_base`, `product`.

## El índice NO es el catálogo
`distributor.catalog.item` es **solo** un índice de búsqueda ligero (metadatos + URLs, **sin binarios**).
No es el producto maestro (`product.template`), ni inventario, ni precios definitivos.

## Búsqueda (`distributor.catalog.item.search_index(query, limit, backend_id)`)
2 fases, siempre por índice: (1) igualdad exacta de código (btree, instantáneo); (2) texto difuso
sobre `search_blob` (un solo GIN/trgm). Sin `ORDER BY` (re-ranking en el consumidor).
Campos: SKU, fabricante, marca, descripción, keywords, categoría, código SAT, código de barras,
e insensible a separadores (`code_norm`). Preparada para semántica (campos `ai_*` → pgvector).

## Caché reemplazable
`lib/cache.py`: `CacheBackend` (interfaz) + `PostgresCacheBackend` (default) + `RedisCacheBackend`
(stub). Se elige con `ir.config_parameter` `catalog.cache_backend`. El Motor no depende de la
implementación.

## Escala (benchmark 1M, STAGING)
Código exacto 0.3 ms · texto común 1–2 ms · texto selectivo 64 ms · todo por índice. Ver
`D3A_MOTOR_CATALOGO_MODELO_INDICES_CACHE_28JUN2026.md`.
⚠️ Tras carga masiva: `ANALYZE distributor_catalog_item` (estadísticas frescas para el planner).

## Pruebas
`odoo -i product_catalog_engine -d <db> --test-enable --test-tags /product_catalog_engine`

## D3c — Catalog Public Interface (REST v1)
Interfaz pública en `/catalog/api/v1` (OpenAPI en `/openapi.json`, Swagger en `/docs`). Endpoints:
`GET /health` (abierto), `GET /products` (búsqueda/filtros/orden/paginación), `GET /products/{ref}`
(detalle + refresco on-demand), `POST /products/{ref}/promote` (idempotente), `GET /metrics`.
Auth por API key (`X-API-Key`) + scopes; rate limiting; `Idempotency-Key`; `X-Request-ID`/
`X-Correlation-ID`; gzip; códigos de error documentados. Lógica en `lib/api_service` (transporte-
agnóstica → GraphQL futuro). Cliente de ejemplo: `tools/catalog_cli.py`. Ver `D3C_*.md`.

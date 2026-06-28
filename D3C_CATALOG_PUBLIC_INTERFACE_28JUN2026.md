# D3c — Catalog Public Interface (REST v1)

**Fecha:** 28-jun-2026 · Módulo `product_catalog_engine` · **Solo STAGING.** Implementa la Especificación v1.0 LTS §10.
REST es la **primera implementación** del contrato público; la lógica vive en la **capa de servicios** (transporte-agnóstica) → GraphQL futuro sin duplicar lógica.

## Base y documentación
- **Base versionada:** `/catalog/api/v1` (desde el día 1).
- **OpenAPI 3:** `GET /catalog/api/v1/openapi.json` · **Swagger UI:** `GET /catalog/api/v1/docs` · **JSON Schema:** `GET /catalog/api/v1/schema/product.json`.
- Objetivo cumplido: un consumidor se integra **solo leyendo la documentación**.

## Endpoints
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/health` | abierto | liveness (status, engine_version) |
| GET | `/openapi.json`, `/docs`, `/schema/product.json` | abierto | documentación |
| GET | `/products` | API key (read) | búsqueda: `q`, filtros (`backend/brand/sat_code/barcode/...`), `sort`, paginación (`page/page_size`) |
| GET | `/products/{ref}` | API key (read) | detalle + frescura; **refresca on-demand si está vencido** |
| POST | `/products/{ref}/promote` | API key (promote) | promueve a Producto Maestro (idempotente) |
| GET | `/metrics` | API key (read) | estado del motor |

## Transversales (todos implementados)
- **Versionado** en ruta (`/v1`); convivencia futura con `/v2`.
- **Auth** por API key (`X-API-Key` o `Authorization: Bearer`) + **scopes** (read/promote).
- **Rate limiting** por key (ventana 60 s) → `429` + `Retry-After` + `X-RateLimit-*`.
- **Idempotencia**: header `Idempotency-Key` en POST (replay del resultado almacenado).
- **Trazabilidad**: `X-Request-ID` (por petición) + `X-Correlation-ID` (propagado o generado).
- **Paginación** (`page`/`page_size`, máx 200), **filtros**, **ordenamiento** (`sort`/`-sort`).
- **Compresión** gzip (si `Accept-Encoding: gzip`).
- **Códigos de error documentados** (envelope `{"error":{"code","message","request_id"}}`): 400 invalid_request, 401 unauthorized, 403 forbidden, 404 not_found, 409 conflict, 422 unprocessable, 429 rate_limited, 500 internal_error, 503 upstream_unavailable.
- **GraphQL futuro**: la capa `CatalogApiService` es transporte-agnóstica; un gateway GraphQL se monta sobre los mismos servicios.

## Consumidores validados (no acoplado a Odoo)
1. **Odoo** — la capa de servicios la usan los tests internos (TransactionCase).
2. **curl** (cliente externo) — `health`/`openapi`/`products`/`detalle`/`promote`/`429` en vivo (STAGING :8075).
3. **CLI Python** (`tools/catalog_cli.py`, urllib puro, sin Odoo) — desde WSL por red: `health` y `search` OK.
El **Portal del Cliente** consumirá esta misma API (idéntico contrato).

## Pruebas y validación en vivo
- **33 tests, 0 failed** (8 de API: servicio search/paginación/refresh-on-stale/promote/health, API key auth+scope+rate-limit, idempotencia, OpenAPI/JSON-Schema).
- **En vivo (STAGING):** health/openapi (200, abiertos) · sin key → **401** · search con key → 200 · detalle → 200 · **promote idempotente → 200 mismo master en ambos intentos** · **rate limit → 200,200,429**. Datos de prueba **eliminados**.

## Decisiones / trampas
- **Lógica en servicios, no en el controlador** (§14 no duplicar lógica).
- `Response` werkzeug manual para control total de headers + gzip.
- **Idempotencia por SQL crudo** en `fetch` (en el contexto público del controlador, el ORM —aun con sudo— lanza `MissingError` por record-rules; SQL lo evita).
- Rate-limit por ventana en el registro de la key (v1; a escala multi-worker conviene un store compartido tipo Redis — ya previsto por la abstracción de caché).

## Objetivo D3c — CUMPLIDO
El Motor de Catálogo **ya puede ser consumido por cualquier aplicación de Alea Systems** (Odoo, Portal, app móvil, IA, scripts) mediante una interfaz pública versionada, documentada (OpenAPI/Swagger/JSON-Schema), segura (key+scopes+rate-limit), trazable e idempotente.

## Siguiente: Release Candidate (sin nuevas funcionalidades)
Por decisión de Enrique, antes de la v1.0 estable se hará un **ciclo de validación RC**: calidad, rendimiento, seguridad, documentación, observabilidad, compatibilidad y despliegue.

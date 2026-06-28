# Especificación Oficial — Motor de Catálogo · **v1.0 LTS** (CONTRATO DE ARQUITECTURA)

**Proyecto estratégico Alea Systems** · 28-jun-2026 · **Estado: 🔒 CONGELADA — Catalog Engine Specification v1.0 LTS.**
El **contrato público permanece estable**. Las mejoras futuras respetan compatibilidad o incrementan la versión según la **Política de Versionado (§15)**, y todo cambio importante requiere un **ADR (§14)**.

> Este documento es la **referencia oficial**. El código **implementa** esta especificación; la especificación **NO depende del código**. Cambios al contrato → nueva versión (ver §7). Detalle de implementación en `BLUEPRINT_*`, `CATALOG_ENGINE_STANDARDS_*`, `D3A_*`, `D3B_*`, `D3D_*`.
> **Catalog Engine 1.0.0.** Estado construido: D0–D3d (en STAGING). Pendiente: D3c (API), luego conectores adicionales.

---

## 0. Principios rectores
1. El **Producto Maestro** (`product.template`) es la fuente de verdad; existe con independencia del proveedor.
2. **Agnóstico al distribuidor**: agregar uno = un conector, sin tocar el núcleo.
3. **El índice NO es el catálogo** ni el inventario ni el precio definitivo.
4. **API-First**: Odoo es un consumidor más.
5. Diseñado para **>1M productos, >20 distribuidores, N consumidores**.
6. **Extender Odoo nativo** antes que reinventar.

---

## 1. Modelo de datos
| Modelo | Rol | Campos clave |
|---|---|---|
| `distributor.backend` | Config por distribuidor | `connector_key`, `partner_id`, `api_url`, `rate_limit`, `timeout`, `retries`, circuit breaker, TTLs caché, políticas imagen/doc, `update_strategy` |
| `distributor.catalog.item` | **Índice** ligero (no maestro, sin binarios) | identidades (§6), `search_blob` (1 col), snapshot indicativo, frescura por canal (§9), `sync_tier`, `provider_snapshot`, `ai_*` (reservados) |
| `product.template` (ext) | **Producto Maestro** | `is_catalog_managed`, `catalog_item_ids`, `distributor_count` |
| `product.supplierinfo` (ext, NATIVO) | Datos del proveedor | `price`(costo), `product_code`, `delay`, `distributor_backend_id`, `distributor_product_id`, `warranty`, `datasheet_url`, `last_sync` |
| `catalog.sync.policy` | TTL por tipo de dato | `data_type`, `backend_id?`, `ttl_minutes` |
| `catalog.run` / `catalog.metric` | Observabilidad | corridas + métricas |
| `catalog.audit.log` | Auditoría append-only | qué/cuándo/old/new/origen |
| `catalog.event` | Eventos persistidos | `name`, `backend_key`, `payload`, `source` |
| `catalog.cache.entry` | Backend de caché Postgres | `key`, `value`, `expires_at` |
| `catalog.dashboard` | Panel de estado | (transitorio) |
**Identidad del índice:** UNIQUE `(backend_id, distributor_product_id)`. **Maestro ↔ índice:** `catalog_item.product_tmpl_id`. **Maestro ↔ proveedor:** `product.supplierinfo` (N por maestro).

## 2. Eventos (contrato)
Forma: `{name, backend_key, payload, source, occurred_at}` (append-only en `catalog.event` + bus en proceso). Catálogo v1.0:
`ProductDiscovered, ProductPromoted, PromotionRequested, PriceUpdated, StockUpdated, PriceChanged, StockChanged, ProductRefreshed, ProductExpired, CatalogSynced, CatalogExpired, DistributorUnavailable, CacheHit, CacheMiss`.
Los suscriptores se **registran** (extensibilidad sin tocar al emisor). Uso: automatización, IA, notificaciones, métricas.

## 3. Interfaces
- **`DistributorConnector`** (ABC): `authenticate()`, `search(query,filters,page)`, `get_product(ref)`, `get_price_stock(refs)`, `normalize(raw)→NormalizedProduct`. Registro por `@register_connector(key, requires_engine)`.
- **`CacheBackend`** (ABC): `get/set/delete/stats`. Implementaciones: Postgres (default), Redis (futuro). Seleccionable por parámetro (reemplazable sin tocar el motor).
- **Servicios** (lib pura, transporte-agnóstica): promoción, búsqueda, scheduler. La UI/API son consumidores.

## 4. Scheduler
- **Canales:** price, stock, enrichment. **Crones por tipo de dato** (cadencias distintas), no uno solo.
- **Regla de oro:** refrescar **SOLO lo vencido** (`<canal>_expires_at <= now`), **ordenado por `sync_tier`**, en **lote** → **JAMÁS recorrido completo**. (Probado: 50k ítems → cron toca solo el lote en <0.5 s.)
- **Tiers:** T0 cotizaciones abiertas · T1 vendidos (90 d) · T2 favoritos · T3 consultados · T4 frío. Recalculados por uso.
- Tras carga masiva: **`ANALYZE`** obligatorio (estadísticas para el planner).
- Cada corrida → `catalog.run` (observabilidad). Detección de calidad (vencidos/backlog/APIs caídas).

## 5. Contratos públicos
- **DTO público estable:** `NormalizedProduct` (§ mapeo en `MAPEO_NORMALIZACION.md`).
- **Superficie pública vs interna:** públicos = modelos y campos documentados + la API (§10) + eventos. Internos (pueden cambiar) = métodos `_*`, lógica de promoción/refresh, normalizadores.
- **Contrato con Membresías** (`CONTRATO_MODULOS_MEMBRESIAS`): el Catálogo **solo** gestiona productos con distribuidor (`is_catalog_managed=True`); **nunca** toca productos propios; comparten solo `product.template`.

## 6. Ownership de datos
| Propietario | Datos | Regla |
|---|---|---|
| **Proveedor** | costo, existencia, garantía, documentos, ficha, código distribuidor, plazo | viven en `supplierinfo`/índice; se actualizan libremente |
| **ERP** | categoría comercial, impuestos, listas de precios, margen, notas, reglas de venta, relacionados propios, `default_code` | el proveedor **NUNCA** los escribe |
| **Mixto** | nombre, descripción, imágenes, atributos | el proveedor los pone y **respeta ediciones manuales** (`provider_snapshot`) |
**Identidades separadas:** Product Master ID · Distributor Product ID · Distributor SKU · Manufacturer SKU · Barcode · SAT Code. **El SKU del distribuidor NUNCA es la identidad del producto.**

## 7. Versionado
- **Motor:** SemVer `ENGINE_VERSION` (1.0.0), independiente de la versión Odoo del manifest.
- **Conectores:** versión propia + `requires_engine` (ej. `>=1.0,<2.0`), validado al registrar.
- **API:** versionada en la ruta (`/catalog/api/v1`) desde el día 1.
- **Contrato (este doc):** v1.0 congelado. *Cambio compatible* → 1.x; *cambio incompatible* → 2.0 con deprecación documentada.

## 8. Reglas de sincronización
- **Idempotencia:** promover/sincronizar N veces nunca duplica (find-or-create por supplierinfo/barcode/default_code entre gestionados).
- **Bajo demanda vs programada:** descubrimiento/alta = on-demand; refresco = scheduler por frescura+tier. **Nunca** full scan del catálogo del distribuidor.
- **Conflictos:** 2 distribuidores, mismo producto → 1 maestro + N `supplierinfo`.
- Auditoría y eventos en cada cambio (no solo precio).

## 9. Políticas de frescura
Por canal: `<canal>_synced_at`, `<canal>_expires_at`, `freshness_status` (never/fresh/expired), `sync_source`. TTL por `catalog.sync.policy` (default: precio 24 h, stock 30 min, enrichment 30 d; imágenes/docs/garantía/descripción ⊂ enrichment). Configurable por distribuidor o global, sin código.

## 10. APIs previstas (contrato que D3c implementará)
- **Base:** `/catalog/api/v1` (versionada). **Auth:** API key / OAuth2 client-credentials + scopes.
- **Endpoints (mín.):** `GET /products` (search: filtros, orden, paginación), `GET /products/{ref}` (detalle + frescura; refresca on-demand si vencido), `POST /products/{ref}/promote`, `GET /health`, `GET /metrics`.
- **Formato:** JSON; DTO = `NormalizedProduct`. **JSON Schema** publicado por entidad. **OpenAPI 3 + Swagger UI**.
- **Cross-cutting OBLIGATORIO:**
  - **Versionado** en ruta (`/v1`).
  - **Idempotencia:** header `Idempotency-Key` en operaciones POST.
  - **Trazabilidad:** `X-Request-ID` (por petición) y `X-Correlation-ID` (propagado entre sistemas); en logs/eventos.
  - **Rate limiting** por consumidor (cabeceras `X-RateLimit-*`, 429 + `Retry-After`).
  - **Paginación** (`page`/`page_size` o cursor), **filtros**, **ordenamiento** (`sort`).
  - **Compresión** (gzip).
  - **Códigos de error documentados** (catálogo estable: 400/401/403/404/409/422/429/5xx + códigos de dominio).
  - **Compatibilidad futura con GraphQL** (la capa de servicios es transporte-agnóstica → un gateway GraphQL podrá montarse sobre los mismos servicios).
- **Objetivo:** un consumidor se integra **solo leyendo la documentación** (OpenAPI/Swagger + JSON Schema + códigos de error).

## 11. Extensión mediante conectores
Agregar un distribuidor = módulo `distributor_<slug>` que implementa `DistributorConnector` + `normalize()` + `distributor.backend`, con `tests/` (fixtures reales) y docs. **Cero cambios** al núcleo. Plantilla de referencia: `distributor_syscom`.

## 12. Decisiones arquitectónicas (ADR) — resumidas, respaldadas por mediciones
- **ADR-1** Híbrido (índice + bajo demanda) en vez de espejar todo (Syscom: 46.8k productos, 36 usados, 7.6 GB imágenes, cron en timeout).
- **ADR-2** `product.supplierinfo` nativo para multi-distribuidor (no columnas por proveedor).
- **ADR-3** Búsqueda en 2 fases (código exacto btree → texto `search_blob` trgm), **sin `ORDER BY`**; medido a 1M: 0.3 ms código / 1–2 ms texto común / 64 ms selectivo (los 3 anti-patrones —OR multicampo, ORDER+LIMIT, stats viejas— corregidos con datos).
- **ADR-4** Caché reemplazable por interfaz (Postgres→Redis sin tocar el motor).
- **ADR-5** Scheduler refresca solo lo vencido por tier (sin full scan): 50k → 200 en 0.48 s.
- **ADR-6** Ownership explícito + respeto a edición manual (`provider_snapshot`).
- **ADR-7** Identidad ≠ SKU; maestro independiente del proveedor (probado: borrar el ítem no borra el maestro).
- **ADR-8** `is_catalog_managed` separa propios de distribuidor (contrato con Membresías).
- **ADR-9** Lib pura sin Odoo (portabilidad + testeo aislado + listo para IA/GraphQL).

## 13. Compatibilidad hacia adelante
- **Campos nuevos del proveedor** → `raw._unknown_keys` (no rompe); se promueven a campo cuando aporten (caso real: `caracteristicas`→`attributes`).
- **DTO aditivo** + **contrato versionado** + **API versionada** (`/v1`).
- **IA reservada** (`ai_*` → pgvector) sin rediseño.
- **Caché y conectores** intercambiables; **GraphQL** futuro sobre la misma capa de servicios.
- **Multi-distribuidor** sin cambios de modelo (probado en vivo con 2º distribuidor).

---

## 14. Filosofía de Evolución (principios permanentes)
Estos principios rigen TODA decisión futura del Motor de Catálogo:
1. **No romper compatibilidad pública.** El contrato público (DTO, API `/v1`, eventos, modelos públicos) es estable; lo incompatible va a una versión mayor con deprecación documentada.
2. **Extender antes que reemplazar.** Se amplía (campos aditivos, nuevos conectores, nuevos endpoints) en lugar de reescribir; se reutiliza lo nativo de Odoo y lo ya construido.
3. **Medir antes de optimizar.** Ninguna optimización sin evidencia (benchmark/medición); las decisiones se respaldan con datos (ver ADRs).
4. **No duplicar lógica.** Una sola fuente de verdad por responsabilidad (servicios transporte-agnósticos consumidos por REST/GraphQL/UI; ownership único por dato).
5. **Todo cambio importante requiere un ADR.** Decisiones de arquitectura documentadas (contexto, opciones, decisión, consecuencias) antes de implementar.

## 15. Política de Versionado (SemVer)
`MAJOR.MINOR.PATCH`. Aplica, por separado, a **Motor**, **Conectores**, **API** y **Especificación**.

| Componente | PATCH (x.y.**Z**) | MINOR (x.**Y**.0) | MAJOR (**X**.0.0) |
|---|---|---|---|
| **Motor** (`ENGINE_VERSION`) | corrección sin cambio de contrato | capacidad nueva compatible (campo aditivo, nuevo servicio) | cambio incompatible de interfaces internas/DTO |
| **Conector** (`distributor_<x>`) | fix de mapeo/llamadas | soporta más datos/endpoints del proveedor | cambia su `requires_engine` mayor o rompe su contrato |
| **API** (`/catalog/api/vN`) | fix sin cambio de forma | endpoint/campo nuevo **opcional**, compatible | cambio incompatible → **nueva ruta `/v2`** (la `/v1` se mantiene durante deprecación) |
| **Especificación** (este doc) | aclaración/corrección editorial | sección/regla nueva compatible | cambio que altera un contrato público |

**Reglas:**
- Romper el contrato público **nunca** es PATCH ni MINOR.
- Un conector declara `requires_engine` (ej. `>=1.0,<2.0`); un MAJOR del Motor obliga a revisar conectores.
- La **API** versiona en la ruta; convivencia de versiones durante el periodo de deprecación anunciado.
- Cada MINOR/MAJOR del Motor o la API → entrada en el changelog + ADR si cambia arquitectura.

---

## Alcance / estado (trazabilidad)
**Implementado y probado en STAGING (no PROD):** D0 línea base · D1 SDK · D2 conector Syscom (referencia) · D3a índice/búsqueda/caché · D3b promoción/maestro · D3d scheduler. **64+ pruebas verdes** acumuladas; benchmarks a 1M (búsqueda) y 50k (scheduler). **Pendiente:** D3c (API, §10) y conectores adicionales.

> **Congelación:** al aprobarse, esta es la **arquitectura v1.0 oficial**. D3c y todo lo siguiente **implementan** esta especificación.

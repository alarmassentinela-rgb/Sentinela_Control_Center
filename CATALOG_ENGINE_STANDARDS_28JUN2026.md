# Catalog Engine — Estándares de Ingeniería y Decisiones de Arquitectura (ADR)

**Proyecto estratégico Alea Systems · Motor de Catálogo · v1.0** · 28-jun-2026
Norte estratégico (criterio #10): **toda decisión debe seguir siendo correcta con >1,000,000 de productos, >20 distribuidores y varios sistemas consumiendo el motor.** Si no, se rediseña ahora.

---

## 1. Convenciones de desarrollo
| Elemento | Estándar | Ejemplo |
|---|---|---|
| **Módulos** | `distributor_connector_base` (SDK), `product_catalog_engine` (motor), `distributor_<slug>` (conectores) | `distributor_syscom`, `distributor_cva` |
| **Modelos Odoo** | prefijo de dominio: `catalog.*` (motor), `distributor.*` (proveedor) | `catalog.run`, `distributor.backend` |
| **Servicios** (lib pura, sin ORM) | `CamelCaseService` en `lib/services/` | `PromotionService`, `PricingService` |
| **Conectores** | clase `<Slug>Connector(DistributorConnector)`, registrada con `connector_key` en minúscula-snake | `SyscomConnector`, key=`syscom` |
| **Eventos** | `PascalCase` en pasado; constante `EVT_<UPPER>` | `ProductPromoted` / `EVT_PRODUCT_PROMOTED` |
| **Excepciones** | sufijo `Error`, jerarquía bajo `CatalogError` | `RateLimitError`, `UpstreamUnavailableError` |
| **Logs** | logger por namespace `odoo.addons.<modulo>`; structured (k=v); nunca secretos | `_logger.info("sync done backend=%s ok=%s", key, n)` |
| **Pruebas** | `tests/test_<unidad>.py`, clases `Test<Unidad>`; tags `catalog`, `<modulo>` | `test_resilience.py::TestCircuitBreaker` |
| **Python** | tipado (type hints) en lib pura; docstrings; `snake_case`; sin lógica en vistas/controladores | — |

## 2. Versionado
- **El motor tiene versión propia** (SemVer): **Catalog Engine 1.0.0** (constante `ENGINE_VERSION` en `lib/version.py`). Independiente de la versión Odoo del manifest (`18.0.1.0.0`).
- **Cada conector versiona aparte** y declara la versión de motor que soporta: `REQUIRES_ENGINE = ">=1.0,<2.0"`.
- **Compatibilidad:** `is_compatible(engine_version, requires)` valida al cargar el conector; incompatibilidad = el conector no se registra y se reporta (no rompe el motor). SemVer: *major* rompe contrato; *minor* agrega; *patch* corrige.

## 3. Eventos (desde D1)
- **Bus de eventos en proceso** (`lib/events.py`, `EventBus`) + **persistencia** (`catalog.event`) + puente opcional a `bus.bus` (realtime) y a automatizaciones Odoo.
- Catálogo inicial: `ProductDiscovered`, `ProductPromoted`, `PriceUpdated`, `StockUpdated`, `CatalogSynced`, `DistributorUnavailable`, `CacheHit`, `CacheMiss`, `PromotionRequested`.
- **Contrato del evento:** `{name, occurred_at, backend_key, payload:{...}, source}`. Append-only.
- Uso futuro: automatizaciones, IA, notificaciones, métricas. **Los suscriptores se registran** (no se modifica el emisor).

## 4. Extensibilidad
- **Interfaces + estrategias + registros**, nunca `if distributor == "syscom"`.
- `DistributorConnector` (ABC) + **registro** por `connector_key` (decorador `@register_connector`). El motor resuelve la clase por la config del `distributor.backend`.
- Puntos de extensión por **registro**: conectores, estrategias de precio/abasto (reglas), políticas de imagen/documento, normalizadores. Todo *pluggable*.

## 5. Seguridad
- **Credenciales en `ir.config_parameter`** (namespaced por backend), **nunca** en columnas de texto plano ni en logs. Accesores `get_secret/set_secret`.
- **Rotación**: método `rotate_credentials()` + fecha `credential_rotated_on`; el token se invalida al rotar.
- **Resiliencia (lib/resilience.py):** **rate limiting** (token-bucket), **reintentos** con **backoff exponencial + jitter**, **circuit breaker** (CLOSED→OPEN→HALF_OPEN), **timeouts configurables** por backend. Todo configurable por distribuidor (R3).

## 6. Calidad (gate de cada entregable)
Tipado · docstrings · **cobertura de pruebas** (unitarias lib + integración Odoo) · lint (flake8/pylint-odoo, líneas ≤120) · validaciones (`@api.constrains`) · **manejo de errores** (jerarquía de excepciones) · **métricas** en toda operación. No se aprueba sin tests verdes.

## 7. Performance (instrumentado desde D1)
Se mide y registra (en `catalog.metric`/eventos): **tiempo de cada llamada API**, **tiempo de normalización**, **tiempo de caché** (y hit/miss), **tiempo de promoción**, **tiempo de sincronización**. Decorador/contexto `@timed(metric)` envuelve cada operación. Objetivo: detectar degradación antes de que afecte.

## 8. Listo para IA (sin rediseñar después)
- **API-First** + DTO estable (`NormalizedProduct`) + **eventos** + **datos limpios** = un agente de IA puede: recomendar, buscar equivalentes, sugerir reemplazos, detectar mejor proveedor, cotizar, detectar anomalías de precio.
- Reservado: campos de embeddings/etiquetas semánticas a futuro; el `price.history` alimenta detección de anomalías; las reglas (R4) exponen "mejor proveedor" por API. La IA es **un consumidor más** de la API.

## 9. Catálogo maestro único (productos propios + distribuidores)
- **`product.template` es el catálogo maestro ÚNICO**: incluye productos/servicios **propios de Alarmas Sentinela** (planes, monitoreo, GPS, servicios) **y** productos de distribuidores.
- Distinción por **origen**, no por modelo separado: `product.supplierinfo` indica qué distribuidores lo ofrecen; un producto **propio** simplemente no tiene supplierinfo de distribuidor. Un mismo producto puede ser propio y además surtible por Syscom/CVA.
- El motor administra ambos; los conectores solo alimentan la parte de distribuidor.

## 10. Criterio rector (escala objetivo)
Cada modelo, índice y proceso se diseña para **1M+ productos / 20+ distribuidores / N consumidores**: índices adecuados (unique (backend, ref), trgm), **paginación/streaming** (nunca cargar todo en memoria), trabajo **asíncrono** (OCA `queue_job`) e **idempotente**, caché con TTL, sincronización **por prioridad** (jamás "recorrer todo"), y API versionada con contrato estable.

---

### Mapa de decisiones → D1 (qué de esto se construye ya)
`lib/version.py` (#2) · `lib/events.py` + modelo `catalog.event` (#3) · `lib/connector.py` registro (#4) · `lib/resilience.py` circuit-breaker/backoff/rate-limit/timeouts (#5) · `lib/dto.py` tipado (#6/#9) · `lib/instrumentation.py` + `catalog.run`/`catalog.metric` (#7) · `catalog.audit.log` (#5/#6) · `distributor.backend` config+secretos+rotación (#3/#5) · tests + README + CLAUDE.md (#6). API-First/IA/reglas (#1,#8) se **reservan** y se exponen en D3+.

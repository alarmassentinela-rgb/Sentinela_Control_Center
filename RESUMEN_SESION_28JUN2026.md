# Resumen de sesión — 28 de junio de 2026

Jornada dedicada a **construir y cerrar el Catalog Engine v1.0 LTS** (primer motor estratégico de Alea Platform), más la **auditoría/congelación de Membresías** y la **documentación de plataforma**. **Todo en STAGING; NADA en PROD.** (Hubo en paralelo otra línea de trabajo —Portal COC, Design System, visión de producto: commits `feat(web)`/`docs(ds)`/`docs(producto)`/`docs(arquitectura)`— no cubierta aquí.)

---

## 1. Catalog Engine v1.0 LTS — del problema Syscom a un motor estratégico
**Diagnóstico:** Syscom estaba espejado casi entero (46,843 productos, **solo 36 con uso**, 0 stock, **~7.6 GB de imágenes**, 980 categorías; cron en **timeout**). Decisión: **modelo híbrido** (Odoo guarda lo usado + consulta bajo demanda + multi-distribuidor por conectores; imágenes/docs por URL).

**3 módulos nuevos (Catalog Engine 1.0.0, solo STAGING):**
- **D0** línea base (`1975c97`): backup STAGING + métricas + lista blanca (103 prod en uso).
- **D1** `distributor_connector_base` (SDK, `6cf3de2`): DTO `NormalizedProduct`, ABC `DistributorConnector`+registro, resiliencia (rate-limit/circuit-breaker/backoff/timeouts), `EventBus`, observabilidad (`catalog.run/metric`), auditoría append-only, `distributor.backend`. **17 tests.**
- **D2** `distributor_syscom` conector de **referencia** (`cdb0200`): `normalize()` puro (100% del detalle: galería/360/docs/garantía/MAP/stock/SAT/dims/atributos), tolerante a nulos, compat-hacia-adelante (`raw._unknown_keys`), `is_error_payload` (Syscom 200+{error}); mapeo de errores 429/500/timeout/401/JSON; métricas por endpoint; **10 fixtures reales**; post_init migra credenciales. **+18 tests + smoke real.**
- **D3a** `product_catalog_engine` índice+búsqueda+caché (`fc7c7ee`): `distributor.catalog.item` (índice ligero, identidades separadas, `search_blob`+GIN/trgm, `ai_*` reservados pgvector), búsqueda **2 fases** (código exacto btree → texto trgm, sin ORDER BY), caché reemplazable (Postgres/Redis). **Benchmark 1M: 0.3 ms código / 1–2 ms texto común / 64 ms selectivo, todo por índice.**
- **D3b** promoción → Producto Maestro (`adb99f8`): idempotente, ownership (proveedor/ERP/mixto con `provider_snapshot`), conflictos (2 distribuidores=1 maestro+N supplierinfo), `is_catalog_managed` (propios nunca tocados), versionado en auditoría. **Probado: el maestro sobrevive aunque se borre el ítem de índice.** +demo real y multi-proveedor en vivo.
- **D3d** scheduler inteligente (`c012596`): frescura por canal + políticas TTL (`catalog.sync.policy`) + tiers por uso + crones que refrescan **solo lo vencido por tier** (sin full scan) + eventos + dashboard. **Benchmark 50k: cron tocó solo 200 por tier en 0.48 s, 49.5k intactos.**
- **D3c** **Catalog Public Interface** REST v1 (`2c2d2a2`): `/catalog/api/v1` (products/detail/promote/health/metrics) + OpenAPI/Swagger/JSON-Schema; auth API key+scopes, rate-limit, idempotencia, X-Request/Correlation-ID, paginación/filtros/orden, gzip; lógica en capa de servicios (GraphQL futuro). **Validado EN VIVO** con 3 consumidores (Odoo, curl, CLI Python): 401 sin key, search/detalle, promote idempotente, rate-limit 200/200/429.

**Especificación congelada (`179cee5`, `d2e7e9a`): Catalog Engine Specification v1.0 LTS** — contrato oficial (el código implementa la spec) + Filosofía de Evolución (§14) + Política de Versionado SemVer (§15).

**Release Candidate (`1e6eb51`): APROBADO, 0 FAIL.** RC-01..RC-10; **68/68 pruebas en BD limpia desde cero** (reproducible). El RC cazó y corrigió un test no reproducible (`a1ae207`). Observaciones → backlog v1.1.

**Cierre (`d076bb5`): Acta de Cierre — proyecto OFICIALMENTE CERRADO.** Arquitectura aprobada · spec v1.0 LTS congelada · RC aprobado · backlog v1.1 documentado · sin pendientes. Mejoras futuras = v1.1 o proyecto independiente.

## 2. Membresías (`sentinela_subscriptions`) — auditada y CONGELADA
- **Auditoría técnica de solo lectura** (`f1e3fc4`): cumple su función, no bloquea la nueva arquitectura. Hallazgos: idempotencia por texto (frágil), cron en 1 transacción, falta de índices, sin tests, single-company.
- **CONGELADA en modo mantenimiento** (`68e13f0`): backlog técnico priorizado (críticas: clave única anti-dup, batching/commit, índices) + **contrato de integración v1.0** (comparte solo `product.template` con el Catálogo; el Catálogo excluye productos propios). **No se tocó PROD.**

## 3. Plataforma y gobernanza (docs)
- **Alea Platform Master Plan** (`79e9834`, luego v2 por Enrique): mapa del ecosistema (Core/Apps/Operations/Intelligence/Integrations) + **regla de 3 preguntas**.
- **Blueprint integración Portal↔Catalog** (`79e9834`): Portal = 1er consumidor; consume Catalog v1 (no Syscom/ORM); el Gateway filtra `cost` (interno).
- **Alea API Gateway** elevado a Core (`0ff6438`): punto único de acceso; sin lógica de negocio.
- **Política de evolución del Portal** (`01982e1`): **Portal prioridad, incremental, sin rehacer**; Gateway = **roadmap, no requisito**; nuevas features → Catalog v1; nada de nuevas llamadas directas a Syscom.

---

## Pendientes / siguiente
1. **Siguiente foco del equipo: Portal de Clientes** (consume Catalog como componente estable, incremental).
2. **Backlog Catalog Engine v1.1** (fuera del proyecto cerrado): USD→MXN · promoción masiva por lote · hash de API keys · rate-limit con Redis · alertas externas · runbook de restore + commit por lote · suite HttpCase + cobertura.
3. **Go-live a PROD del Catalog Engine: decisión y plan aparte** (hoy todo vive en STAGING).
4. **Membresías:** deuda técnica administrada, NO implementar hasta estabilizar el ERP (módulo congelado).

## Verificaciones reales hechas
- **68 pruebas, 0 fallos** (incl. instalación desde cero en BD limpia sin demo, reproducible 2×).
- Benchmarks medidos: búsqueda 1M (0.3–64 ms), scheduler 50k (0.48 s sin full scan), promoción idempotente.
- API pública validada **en vivo** (curl + CLI Python + Odoo): auth/401, search, detalle, promote idempotente, rate-limit 429.
- **Sin validar / pendiente:** go-live PROD (no realizado); USD→MXN y promoción por lote (backlog v1.1).

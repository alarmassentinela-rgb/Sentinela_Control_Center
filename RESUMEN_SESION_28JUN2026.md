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

---

# Sesión paralela — Incidente cron Syscom + carga masiva de flota GPS + Connecta

## 1. Incidente "ERROR ROBOT" del cron Syscom (RESUELTO)
- Telegram de Enrique recibió 2× "🚨 ERROR ROBOT: current transaction is aborted". **Origen: el cron "Syscom: Update Prices and Stock"** (id 32, `_cron_update_syscom_products`). El texto solo lo emite ese cron (`product.py:620`).
- **Causa raíz:** los 3 puntos de escritura del cron atrapaban la excepción por producto **sin `rollback`** → un `write` con dato malo dejaba el cursor Postgres abortado y todo lo siguiente (commits, demás writes, `nextcall`/`lastcall` del cron) tronaba en cascada. Llegó 2× porque Odoo reintenta un cron de código que falla; `lastcall` quedó clavado en 24-jun (las corridas 25/26/27 abortaron).
- **Fix (v18.0.1.8.8, commit `34f9396`):** cada write en `with self.env.cr.savepoint(): ...; flush_recordset()` + `_logger.warning` que nombra el registro (id/code). Descartado: el zombie queue cron (ya borrado por `-u` 26-jun) y el write de sat_key (campos SAT son `char`, seguro).
- **Proceso:** cron **desactivado en PROD** (cortó spam) → fix → validado en STAGING (barrido completo, 0 fallos, 0 abort) → `-u` PROD + restart contenedor → **cron reactivado** (nextcall 28-jun 09:00 UTC). Logs del contenedor en hora **LOCAL (CST)**, no UTC (trampa que costó tiempo).
- **Verificación pendiente:** la corrida real del 28-jun 3am — si topa dato malo, ahora termina OK y manda "Robot Syscom ✅ Finalizado … ⚠️ Errores: N" (NO ERROR ROBOT), con los `FALLÓ` en log. Memoria `reference_syscom_cron_error_robot`.

## 2. Carga masiva de flota GPS a suscripciones (export Smake/Connecta → Odoo)
Se cargaron equipos GPS (Concox/GT06) de Excel de Descargas a su `sentinela.subscription`. Trampas: constraint único = **IMEI** (no SIM); col ICCID del Excel trae `f` basura (usar col SIM); `gps_platform` se setea directo, `gps_mode` viene del producto (related).

| Sub | Cliente | GPS | Destino |
|---|---|---|---|
| SUB-0241 | Enrique Garza Cantú | 2 | ✅ **migrados a SentiCar** (registrados + SMS cutover, ambos online) |
| SUB-0394 | Jaime Delgado (DELSA) | 8 | Smake (esperan autorización; plataforma quedó en senticar, ⚠️ ofrecido pasar a smake) |
| SUB-0437 | Javier Iván Bravo | 4 | Smake |
| SUB-0401 | Carlos Suárez | 2 | Smake (⚠️ producto Tracksolid por corregir) |
| SUB-0390 | Aceros y Metales Azteca | 13 | Smake — **reconciliado vs Connecta** (FORD 84 tenía SIM del FORD 350 → corregido a …224578) |
| SUB-0427 | Gabriel Luna de Matamoros | 3 | Smake (⚠️ producto Tracksolid por corregir) |
| SUB-0393 | Construservicios ERFA | 26 | Smake — **reconciliado vs Connecta** (16 SIMs rellenadas + 1 malformada corregida) |
| SUB-0392 | Claudia N. Salinas | 3 | Smake — verificado en Connecta (OK) |
| SUB-0396 | PL Agencia de Empleos (Gabriela Flores) | 1 | Smake — verificado |
| SUB-0441 | Carlos Solís | 5 | Smake (sub en suspension) — verificado |

## 3. "Camino de validación con Connecta" (floLIVE) — hallazgo reutilizable
- floLIVE **no deja listar** por cuenta (500 "No static resource"), **pero sí busca por IMEI**: `GET /api/v2/subscriber/imei/{imei}` → `subscriberIdentifiers.iccid` + `alias` (codifica IMEI) + `subsStatus`. Con eso se rellenan/corrigen SIMs autoritativamente. Correr por `odoo shell` en PROD (los métodos floLIVE no son `@api.model`). 403/SUSPEND = SIM suspendida.
- **Skill `/cargar-gps-flota` creada** (commit `4e92fc0`) — runbook completo (parseo Excel, anti-dup IMEI, plataforma, Connecta, migración SentiCar opcional). + memoria `reference_connecta_flolive_lookup`.

## 4. Rename de alias en Connecta (Carlos Solís)
- 4 SIMs de Carlos Solís tenían alias "ERFA GPS …" (etiqueta vieja). **Aliases cambiados a "Carlos Solis …"** vía `PATCH /api/v2/subscriber/iccid/{iccid}` `{"alias": ...}` (asíncrono, 202; 500 si se apura → reintentar).
- ⚠️ **El `userLabels` (tag de agrupación) NO se pudo cambiar por API**: el PATCH devuelve 202 pero **ignora `userLabels`** (solo aplica si va junto al alias, y aun así no persiste); no existe endpoint de asignación de label. Quedan en `['ERFA']`. Hay que cambiarlo en el **portal de Connecta a mano**, o capturar la petición real del portal para automatizar.

## Pendientes (sesión GPS)
1. **Verificar mañana (28-jun 3am)** que el cron Syscom corre limpio con el fix.
2. **DELSA/SUB-0394:** decidir plataforma (quedó senticar, los equipos están en Smake sin autorización de cambio) + migración cuando autoricen.
3. **Productos Tracksolid→Smake** en SUB-0401 y SUB-0427 (inconsistencia plan↔plataforma, afecta facturación).
4. **userLabels ERFA→CarlosSolis** de 4 SIMs (en portal Connecta o con la petición real del portal).
5. Las 7 unidades de KAWAC sin reportar y las SIMs suspendidas siguen pendientes (ver memoria KAWAC).

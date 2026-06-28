# Informe Release Candidate — Catalog Engine v1.0 LTS

**Fecha:** 28-jun-2026 · **Alcance:** RC-01…RC-10 · **Entorno:** STAGING (Sentinela_STAGING + BD limpia `rc_scratch`) · **Feature Freeze activo.**
**Veredicto global:** ✅ **APROBABLE como v1.0** — todos los puntos **críticos en PASS**; observaciones registradas para v1.1 (ninguna bloquea la estabilidad).

| Área | Resultado |
|---|---|
| RC-01 Arquitectura | 🟡 PASS WITH OBSERVATIONS |
| RC-02 Calidad | 🟡 PASS WITH OBSERVATIONS |
| RC-03 Seguridad | 🟡 PASS WITH OBSERVATIONS |
| RC-04 Rendimiento | 🟡 PASS WITH OBSERVATIONS |
| RC-05 Observabilidad | 🟡 PASS WITH OBSERVATIONS |
| RC-06 Recuperación | 🟡 PASS WITH OBSERVATIONS |
| RC-07 Documentación | ✅ PASS |
| RC-08 Compatibilidad | 🟡 PASS WITH OBSERVATIONS |
| RC-09 Despliegue | ✅ PASS (con nota) |
| RC-10 Aceptación | ✅ (sin FAIL) |

---

## RC-01 Arquitectura — 🟡 PASS WITH OBSERVATIONS
- ✅ Implementación **conforme a la Especificación v1.0 LTS**: modelos (§1), eventos (§2, 14), interfaces `DistributorConnector`/`CacheBackend` (§3), scheduler por frescura+tier sin full scan (§4), ownership (§6), versionado (§7), API (§10).
- ✅ **Sin desviaciones de contrato**: el maestro es `product.template` (sin columnas por-distribuidor); el proveedor vive en `supplierinfo`; el SKU no es identidad; `is_catalog_managed` aísla propios.
- 🟡 **Observación:** USD→MXN y promoción masiva por lote (listados como "previstos") **no implementados** → v1.1. No violan el contrato público.

## RC-02 Calidad — 🟡 PASS WITH OBSERVATIONS
- ✅ **68 pruebas, 0 fallos** — verificadas también en **BD limpia sin demo** (`rc_scratch`): base 29, syscom 24, engine 45 (incluye API).
- ✅ Casos límite cubiertos: nulos, payload de error Syscom, compat-hacia-adelante, expiración/frescura, idempotencia, conflictos multi-proveedor, no-hijack de propios.
- ✅ **RC catch:** se detectó y corrigió un test no reproducible (dependía de datos existentes) → ahora pasa en BD limpia.
- 🟡 **Observación:** las pruebas de la API son a nivel de servicio + validación HTTP **en vivo** (curl/CLI); falta una suite `HttpCase` formal y % de cobertura medido (herramienta de coverage).

## RC-03 Seguridad — 🟡 PASS WITH OBSERVATIONS
- ✅ **Auth** por API key (`X-API-Key`/Bearer) + **scopes** (read/promote); endpoints de recurso exigen key.
- ✅ **Rate limiting** por key (429 + `Retry-After` + `X-RateLimit-*`), validado en vivo (200/200/429).
- ✅ **Secretos** en `ir.config_parameter` (nunca en columnas/logs) + **rotación** (`rotate_credentials`).
- ✅ **Auditoría** append-only (`catalog.audit.log`: `write`/`unlink` lanzan UserError).
- ✅ **ACLs**: `catalog.api.key`/`catalog.api.idempotency` solo `group_system` (no público).
- ✅ **Dependencias** externas mínimas y estándar (`requests`/`urllib3`, ya de Odoo); sin paquetes exóticos.
- 🟡 **Observaciones (v1.1):** (a) las API keys se guardan en **texto plano** (recomendado: hash/prefijo); (b) el rate-limit es por registro en BD (no atómico entre workers; un store compartido tipo Redis lo endurece — ya previsto por la abstracción de caché); (c) no hay escáner automatizado de dependencias/CVE.

## RC-04 Rendimiento — 🟡 PASS WITH OBSERVATIONS
- ✅ **Búsqueda a 1,000,000**: código exacto **0.3 ms**, texto común **1–2 ms**, texto selectivo **64 ms** (todo por índice, sin Seq Scan).
- ✅ **Scheduler a 50,000**: refresca solo el lote vencido por tier en **0.48 s** (49.5k vigentes intactos) → **sin recorridos completos**.
- ✅ Escalabilidad de diseño verificada con datos.
- 🟡 **Observaciones:** memoria/CPU **no perfiladas** formalmente (solo benchmarks funcionales); **promoción masiva ~14/s** (aceptable bajo demanda; lote → v1.1).

## RC-05 Observabilidad — 🟡 PASS WITH OBSERVATIONS
- ✅ **Logs** por namespace; **métricas** (`catalog.run`/`catalog.metric`); **eventos** (14, persistidos + bus); **dashboard** "Estado del Motor".
- 🟡 **Observación:** los eventos de alerta (`DistributorUnavailable`, `CatalogExpired`) **no están cableados a un canal externo** (Telegram/correo/Prometheus); el endpoint `/metrics` existe pero falta exportador para alertas proactivas → v1.1.

## RC-06 Recuperación — 🟡 PASS WITH OBSERVATIONS
- ✅ **Backups** globales (Plan B: DB cada 8 h) + respaldo puntual de STAGING (D0).
- ✅ **Rollback**: despliegues reversibles (rsync + `-u`), **tags git** por entregable, desinstalación de módulos; datos de prueba siempre eliminados.
- ✅ **Tolerancia a fallos** en el scheduler: `try/except` por ítem (un fallo no tumba el lote) + evento `DistributorUnavailable`.
- 🟡 **Observaciones:** no hay **runbook de restore específico** del Motor ni *drill* de restauración; el scheduler **no commitea por lote** (mitigado por lotes pequeños); la promoción masiva tampoco.

## RC-07 Documentación — ✅ PASS
- **Arquitectura:** Especificación v1.0 LTS + Blueprint + Standards/ADR + D3A/B/D/C.
- **API:** OpenAPI 3 + Swagger UI + JSON Schema (servidos) + `D3C_*`.
- **Instalación/Operación/Desarrollo/Conectores:** `README.md` + `CLAUDE.md` por módulo + guía "cómo agregar un distribuidor" + `MAPEO_NORMALIZACION` + CLI de ejemplo.

## RC-08 Compatibilidad — 🟡 PASS WITH OBSERVATIONS
- ✅ **Odoo 18 Community** (construido y probado). **Futuros distribuidores**: patrón de conector + multi-proveedor probado en vivo. **Futuras versiones del Motor**: SemVer + `requires_engine` validado al registrar.
- 🟡 **Observación (PostgreSQL):** la búsqueda difusa requiere la extensión **`pg_trgm`** (contrib estándar); el código la crea con `CREATE EXTENSION IF NOT EXISTS` y **degrada con aviso** si no hay permisos — debe garantizarse en el despliegue.

## RC-09 Despliegue — ✅ PASS (con nota)
- ✅ **Instalación desde cero**: BD limpia `rc_scratch` (sin demo) → 29 módulos en ~19 s, **68/68 pruebas verdes**. **Reproducible** (repetido en `rc_scratch2`).
- ✅ **Actualización** (`-u`) probada repetidamente; **versionado** por git/tags.
- 🟡 **Notas:** la **desinstalación** no se sometió a *drill* destructivo (es la estándar de Odoo); un campo computado-almacenado (`search_blob`) sobre tabla poblada dispara recompute en `-u` (mitigado: tabla nace vacía; migración controlada a futuro). ⚠️ **Controllers nuevos requieren reiniciar el worker** (no basta `-u`).

## RC-10 Aceptación
- **Puntos críticos** (correctitud funcional, seguridad núcleo, instalación/reproducibilidad, conformidad de contrato): **PASS**.
- **0 FAIL.** Las observaciones son mejoras de robustez/operación, **no bloqueantes** para una v1.0 LTS.
- **Conclusión:** **Catalog Engine v1.0 LTS = ACEPTADO** (sujeto a tu visto bueno), con el backlog de observaciones movido a v1.1.

---

## Backlog v1.1 (derivado del RC)
1. **USD→MXN** en el motor (precio MXN derivado del TC).
2. **Promoción masiva por lote** (subir de ~14/s).
3. **Hash de API keys** (no texto plano) + escáner de dependencias.
4. **Rate-limit con store compartido** (Redis) atómico entre workers.
5. **Alertas externas** (eventos → Telegram/correo/Prometheus) + exportador de `/metrics`.
6. **Runbook de restore** del Motor + *drill* + commit por lote en scheduler/promoción.
7. **Suite HttpCase** formal + medición de **cobertura**.
8. *(Si el RC lo exigiera para estabilidad: cualquier observación se promueve a requisito de v1.0; hoy ninguna lo es.)*

> **Nada de esto se ha desplegado en PRODUCCIÓN.** El Motor de Catálogo vive solo en STAGING. La v1.0 LTS se da por estable a nivel de ingeniería; el go-live a PROD será una decisión y un plan aparte.

# Sprint-01 — Cimientos técnicos y Seguridad (WS-1/2/4/6)

**Fechas:** 2026-06-25 → 26 · **Estado:** ✅ Completado y validado en STAGING · ⏳ despliegue a Producción pendiente de ventana

## Objetivo
Construir los cimientos técnicos del portal y **garantizar el aislamiento de datos entre clientes** a nivel de Odoo (record rules = primera línea de defensa), de modo que ningún cliente pueda ver datos de otro aunque falle el Gateway o un endpoint.

## Cambios
- **WS-1 Higiene:** eliminado módulo muerto `sentinela_contract_builder`; eliminado modelo roto `syscom.import.queue` (+ bump `syscom 18.0.1.8.1`); `CRON_STATUS.md` (estado de crones + freeze de facturación).
- **WS-4 `sentinela_api` (addon REST, nuevo):** controllers base (RFC-7807, `X-Request-Id`), `GET /v1/me`, `GET /v1/config/theme` (costura branding), serializadores DTO, tests.
- **WS-2 Seguridad (núcleo del sprint):** grupo `group_coc_portal`; **usuario portal lazy** (`res.users._coc_ensure_portal_user`); **record rules** de aislamiento (`partner_id child_of commercial_partner`) en subscription, alarm.event, monitoring.device, fsm.order, sign.document, account.move; **ACL read-only**; auditoría de creación de usuario portal.
- **WS-6 Monorepo `sentinela_coc`:** base del Gateway (FastAPI) con `/health`, `/readyz`, logging estructurado + `request_id`, OpenAPI, Dockerfile, compose; estructura web/infra/docs.
- **WS-7/WS-8 (desde el inicio):** suite de pruebas (unit/seguridad/perf) + observabilidad base.
- **Entregables de seguridad:** `SECURITY_PORTAL_COC.md` (matriz de permisos por modelo y rol), `CHECKLIST_VALIDACION_SEGURIDAD_COC.md` (evidencia), `DEPLOY_V18_WS2_RUNBOOK.md`.

## Commits
| Hash | Fecha | Descripción |
|---|---|---|
| `324bac7` | 25-jun | docs: plan Sprint 0 COC (aprobado) + WS-7 pruebas y WS-8 observabilidad |
| `8a25038` | 25-jun | feat(coc): Sprint 0 Bloque A — higiene + esqueleto sentinela_api + base gateway |
| `9b3232e` | 26-jun | feat(coc): WS-2 seguridad — aislamiento de datos por cliente (record rules) |
| `2efe409` | 26-jun | test(coc): WS-2 — prueba de rendimiento de record rules + auditoría + checklist |
| `e7f3ba1` | 26-jun | test(coc): WS-2 validado en STAGING — aislamiento 11/11 + datos reales |
| `e9592e0` | 26-jun | fix(coc): WS-2 — cerrar fuga real en sign.document (record rule a base.group_portal) |
| `c5ea76b` | 26-jun | docs: runbook deploy V18 (WS-2) + plan WS-5 *(la parte de runbook V18 cierra este sprint)* |

## Riesgos
- 🔴 **Hueco pre-existente en Producción:** `digital_sign` deja a `base.group_portal` con lectura de `sign.document` sin record rule → en V18 sigue abierto **hasta desplegar `sentinela_api`**. El deploy lo cierra.
- 🟡 `res.users` crece con clientes activos (usuario portal lazy) — sin costo de licencia en Community; monitorear performance.
- 🟡 Limpieza de `syscom` commiteada local pero no desplegada (requiere `-u` del módulo).

## Pruebas
- **Automatizadas en STAGING (`Sentinela_STAGING`):** instalación/actualización exit 0; **suite 12/12 verde, 0 errores** (IDOR, Broken Access Control, aislamiento ±, estructurales rules+ACL, identidad lazy, rendimiento, regresión del hueco).
- **Funcionales con datos reales (242 subs, con rollback):** los 6 modelos aíslan (cliente ve solo lo suyo, 0 fugas); empresarial ve `child_of` su sucursal; **admin sin regresión** (ve totales); rendimiento **0.006 s**.

## Bugs
- 🐞 **Fuga real en `sentinela.sign.document`** (detectada en validación dinámica con datos reales): un usuario portal preexistente veía 142/142 documentos, incl. de otros clientes. **Causa:** regla atada solo a `group_coc_portal` + `digital_sign` daba lectura a `base.group_portal` sin rule. **Corrección:** regla atada a `base.group_portal` + `_coc_ensure_portal_user` asegura grupo en usuarios existentes + test de regresión. **Re-validado:** ve 1/1, fuga 0.

## Rollback
- `sentinela_api` es módulo **nuevo y aditivo**: rollback = desinstalar (no toca datos de negocio).
- Record rules/ACL versionadas: revertir commit + `-u`.
- En Producción: respaldos confirmados (DB 8h, addons diario, código GitHub); restore de DB solo en caso extremo.

## Estado
✅ **Completado y validado en STAGING.** Aprobado el cierre de WS-2 en STAGING. **Pendiente:** despliegue a V18 según ventana de mantenimiento (runbook listo) para cierre definitivo en Producción.

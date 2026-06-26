# Sprint-03 — Cierre / Release Candidate para Producción

**Fechas:** 2026-06-26 → · **Estado:** 🚧 En curso (RC en preparación)

## Objetivo
Dejar listo el **Release Candidate (RC1)** de WS-2 + WS-5 + EvoApi para una **ventana única de despliegue a Producción**, con toda la documentación, validaciones de seguridad/rendimiento y observabilidad. **No se despliega** hasta que el RC esté 100% en verde y la instancia WhatsApp esté reconectada (smoke real de OTP).

## Alcance del RC1
- **WS-2** — aislamiento de datos por cliente (record rules) [validado STAGING].
- **WS-5** — identidad: OTP, sesiones cortas, dispositivos, magic links, contraseñas/recuperación, cambio de teléfono [29–36/36 + 8/8 e2e].
- **Integración EvoApi** — proveedor OTP real resiliente [36/36; health real OK; instancia WA por reconectar].

## Entregables (este Sprint)
| # | Entregable | Documento | Estado |
|---|---|---|---|
| 1 | Release Notes | `RELEASE_NOTES_COC_RC1.md` | ✅ |
| 2 | Runbook de despliegue + Rollback | `DEPLOY_RUNBOOK_COC_RC1.md` | ✅ |
| 3 | Checklist de Producción | `PRODUCTION_CHECKLIST_COC_RC1.md` | ✅ |
| 4 | Smoke Tests | `SMOKE_TESTS_COC.md` | ✅ |
| 5 | PenTest | `SECURITY_PENTEST_COC.md` | ✅ (probes en STAGING) |
| 6 | Validación de rendimiento | `PERFORMANCE_COC.md` | ✅ |
| 7 | Observabilidad (logs/métricas/alertas) | `OBSERVABILITY_COC.md` | ✅ |
| 8 | Checklist final de aceptación | `ACCEPTANCE_CHECKLIST_COC_RC1.md` | ⏳ (gate del go-live) |

## Pendiente para cerrar (operativo, no de desarrollo)
- Reconectar instancia WhatsApp `SentinelaWA` (Enrique) → **smoke real de OTP**.
- Aprobación del Checklist final de aceptación → programar ventana única.

## Commits
Ver tabla de cada documento + bitácora. Versión RC: `sentinela_api 18.0.0.1.0`, `coc-gateway 0.2.0`.

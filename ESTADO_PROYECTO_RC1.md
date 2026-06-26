# Estado del Proyecto — Portal COC · RC1 (Resumen Ejecutivo)

**Fecha:** 2026-06-26 · **Estado:** 🧊 **FEATURE FREEZE (RC1)** — solo correcciones del smoke final / despliegue.
**Componentes:** `sentinela_api 18.0.0.1.0` (Odoo addon) · `coc-gateway 0.2.0` (FastAPI).

## 1. Qué es
Plataforma **base** del Centro de Operaciones del Cliente (COC): capa de **seguridad e identidad** sobre Odoo 18, lista para que clientes externos se autentiquen y la API exponga datos **aislados por cliente**, sin duplicar lógica de negocio. Base para el desarrollo funcional del Portal (Sprint 1+) y para una futura plataforma multiempresa.

## 2. Alcance entregado (RC1)
- **WS-2 — Aislamiento de datos por cliente** (record rules Odoo = 1ª línea de defensa).
- **WS-5 — Identidad y sesiones:** OTP (proveedor desacoplado), sesiones cortas (access revocable + refresh rotativo con detección de reuse), dispositivos confiables, magic links de un solo uso, contraseñas Argon2 + recuperación, cambio seguro de teléfono, revocación al cambiar credenciales, auditoría completa.
- **Integración EvoApi** — proveedor OTP real resiliente (health, circuit breaker, reintentos, métricas; sin loguear secretos/OTP).
- **Hardening:** restricción LAN (allowlist) + secreto compartido en endpoints internos.
- **Observabilidad:** logs estructurados (`request_id`), `/metrics`, `/v1/providers/health`, alert checker → Telegram.

## 3. Validación (STAGING)
| Frente | Resultado |
|---|---|
| Suite Gateway (unit) | **36/36** ✅ |
| E2E Gateway↔Odoo (datos reales) | **8/8** ✅ |
| Suite Odoo `sentinela_api` | **19/19** ✅ |
| PenTest (probes activos) | **6/6** ✅ |
| Aislamiento por cliente (6 modelos) | ✅ datos reales |
| Rendimiento | record rules 0.006 s · login ~28 ms · sesiones ~13 ms · health ~2.3 ms |

## 4. Cronología (sprints)
- **Sprint-00** — Análisis, arquitectura y diseño (PRD, auditorías, wireframes). ✅
- **Sprint-01** — Cimientos + seguridad (WS-2). ✅ STAGING.
- **Sprint-02** — Identidad (WS-5) + EvoApi. ✅ STAGING.
- **Sprint-03** — Cierre / RC1 (release notes, runbook, pentest, perf, observabilidad, operación 24×7, arquitectura, inventario, ADRs). ✅ (gate de aceptación pendiente).

## 5. Pendiente para el Go-Live (operativo, NO de desarrollo)
1. Reconectar instancia WhatsApp `SentinelaWA` (actualmente `close`).
2. **Smoke real de OTP** (envío→recepción→verificación→login).
3. Completar **Acceptance Checklist** (smoke + respaldos + aprobación).
4. **Ventana única de despliegue** (Runbook): `sentinela_api -i` en V18 + gateway + fijar CIDR LAN + alertas en cron.
5. Cerrar RC1 (completar `CIERRE_RC1_COC.md`) → abrir **Sprint 1**.

## 6. Riesgos residuales
- Instancia WhatsApp debe mantenerse conectada (fallback: contraseña). Alertado.
- 43% de subs sin teléfono → adopción del login OTP (campaña de captura).
- CFDI PDF se re-renderiza por llamada → caché en Sprint 1.
- Deuda técnica heredada (god-object `subscription.py`, `except:pass`) → se paga en paralelo.

## 7. Versionado / Tags
- **RC1:** tag `coc-v1.0.0-rc1` (este estado, congelado).
- **Go-Live 1.0.0:** tras smoke verde + despliegue exitoso → tag `coc-v1.0.0` (ver procedimiento en §8 de `DEPLOY_RUNBOOK_COC_RC1.md` / abajo).

### Procedimiento para etiquetar 1.0.0 (tras Go-Live)
```bash
# 1. Asegurar que main contiene exactamente lo desplegado y validado en prod
git checkout main && git pull
# 2. Tag anotado de release
git tag -a coc-v1.0.0 -m "Portal COC 1.0.0 — plataforma base en Produccion (WS-2 + WS-5 + EvoApi)"
git push origin coc-v1.0.0
# 3. Completar CIERRE_RC1_COC.md (seccion 6 Estado de Produccion) y abrir Sprint 1
```

## 8. Veredicto
RC1 **técnicamente listo y congelado**. El Go-Live depende únicamente de la reconexión de WhatsApp y de los pasos operativos del cierre.

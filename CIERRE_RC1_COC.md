# Documento de Cierre — Plataforma Base COC (RC1)

> **Estado:** RC1 **APROBADO PARA PRODUCCIÓN** (27-jun-2026, smoke real OK). Las secciones con ⏳
> (datos de Producción) se completan AL FINALIZAR el Go-Live. Marca el cierre de la plataforma
> base (WS-2 + WS-5 + EvoApi) y habilita el inicio del desarrollo funcional (Sprint 1) tras el despliegue.

## 1. Arquitectura final
- **Híbrida API-first, 3 capas + gateway:** SPA → **API Gateway/BFF (FastAPI, `sentinela_coc/gateway`)** → **addon Odoo `sentinela_api` (REST)** → Odoo 18 (`sentinela_*`, fuente de verdad).
- **Identidad** en el gateway (OTP/contraseña/biométrico-dispositivo; sesiones cortas). **Autorización** en Odoo (record rules) vía **sesión efímera** del usuario portal (sin credenciales permanentes).
- **Proveedores desacoplados:** OTP (Mock/EvoApi), cliente Odoo (Http/Fake). Config 100% por entorno.
- Single-tenant con **costuras** documentadas para multiempresa/white-label futuro.

## 2. Componentes implementados
| Componente | Versión | Rol |
|---|---|---|
| `sentinela_api` (Odoo addon) | 18.0.0.1.0 | REST + record rules + handshake sesión efímera + endpoints internos (resolve/set_phone/session) |
| `coc-gateway` (FastAPI) | 0.2.0 | Identidad/OTP/sesiones/dispositivos/magic links/contraseñas + EvoApi + observabilidad |
| `infra/alerts/alert_checker.py` | — | Alertas → Telegram |

Capacidades: aislamiento por cliente (WS-2); OTP + sesiones cortas (access revocable, refresh rotativo+reuse); dispositivos confiables; magic links un-solo-uso; contraseñas Argon2/recuperación/cambio de teléfono; EvoApi resiliente (health/circuit breaker/retries/métricas).

## 3. Métricas obtenidas
- **Seguridad:** suite gateway 36/36 · e2e datos reales 8/8 · Odoo seguridad 19/19 · pentest 6/6.
- **Rendimiento (STAGING):** record rules 0.006 s; login ~28 ms; sesiones ~13 ms; health ~2.3 ms.
- **Smoke real de OTP (27-jun, EvoApi `SentinelaWA` open):** envío OTP por WhatsApp **0.56 s** (latencia proveedor 539 ms); verify→login OK (access+refresh); `/v1/me` devolvió el partner correcto; record rules OK (portal ve solo lo suyo; lectura cruzada denegada); auditoría (otp_request/otp_sent/otp_verify/login/login_new_device + session_open en Odoo); métricas `otp_send_total{ok}=1`, `otp_provider_up=1`; logs sin errores y **sin fuga de OTP/secretos**.
- ⏳ **Producción:** tiempos reales post-deploy (se llenan tras el Go-Live).

## 4. Riesgos residuales
- Instancia WhatsApp `SentinelaWA` debe mantenerse conectada (fallback: contraseña). Alertado.
- 43% de subs sin teléfono → impacta adopción del login OTP (campaña de captura).
- CFDI PDF se re-renderiza por llamada → requiere caché en Sprint 1.
- Crecimiento de `res.users` (usuario portal lazy) — sin costo de licencia; monitorear.
- Deuda técnica heredada (god-object `subscription.py`, `except:pass`) se paga en paralelo.

## 5. Lecciones aprendidas
- La **validación dinámica con datos reales** detectó fugas/bugs que las pruebas sintéticas no veían (hueco `sign.document`; sid malformado; concurrencia de refresh). Validar siempre contra el sistema vivo.
- Desacoplar proveedores (Mock primero) permitió validar TODO el flujo sin servicios externos y reduce el riesgo de integración.
- Record rules como **primera línea** (no el gateway) hace el aislamiento robusto ante bugs de aplicación.
- ⏳ (añadir lecciones del Go-Live).

## 6. Estado de Producción
- **RC1: ✅ APROBADO PARA PRODUCCIÓN** (validación técnica completa + smoke real OTP en verde, 27-jun-2026).
- 🚫 **Despliegue a Producción: NO ejecutado** — pendiente de autorización de Enrique para la ventana única.
- ⏳ Fecha de Go-Live: ____ (al ejecutar la ventana con `DEPLOY_RUNBOOK_COC_RC1.md`)
- ⏳ Resultado del smoke post-deploy: ____
- ⏳ WS-2 / WS-5 cerrados en Producción: ____ · tag `coc-v1.0.0`: ____
- ⏳ Observabilidad/alertas activas en prod (cron alert_checker + CIDR LAN fijado): ____

---
**Cierre oficial de la plataforma base** y arranque de **Sprint 1** (Mis Servicios + Facturación) — ver `SPRINT_1_PLAN_COC.md`.

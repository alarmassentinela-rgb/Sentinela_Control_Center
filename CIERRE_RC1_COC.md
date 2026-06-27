# Documento de Cierre — Plataforma Base COC (RC1)

> **Estado:** ✅ **RC1 DESPLEGADO EN PRODUCCIÓN (27-jun-2026)** — smoke post-deploy en verde.
> Cierre oficial de la plataforma base (WS-2 + WS-5 + EvoApi). Habilita el inicio de Sprint 1.

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
- **RC1: ✅ DESPLEGADO EN PRODUCCIÓN** (27-jun-2026).
- **Componente A** (`sentinela_api` en `Sentinela_V18`): instalado (exit 0, registry OK), grupo + 5 record rules + ACL + auditoría verificados; smoke de aislamiento OK (cliente ve solo lo suyo; admin ve 392; cross-read denegado); **sin regresión interna**.
- **Componente B** (Gateway en `/opt/sentinela_coc`, contenedor `gateway-gateway-1` + `gateway-gateway-db-1`): `/health` ok, EvoApi `healthy`.
- **Smoke post-deploy (OTP real):** envío 0.38 s → verify→login OK → `/v1/me` partner correcto (id 3) → record rules OK → auditoría completa (otp_request/otp_sent/otp_verify/login/login_new_device + session_open) → métricas OK → logs sin fuga de OTP/secretos.
- **Hardening:** allowlist LAN (`coc_internal_allowed_cidrs`) aplicado + verificado (gateway pasa, externo bloqueado); secreto compartido sembrado.
- **Observabilidad:** `/metrics`, `/v1/providers/health`, `/health`; cron `alert_checker` cada 5 min (logs). *Pendiente menor: token Telegram para envío de alertas.*
- **Tag:** `coc-v1.0.0`.
- **Ingreso público `api.sentinela.mx`** (NPM/Cloudflare): pendiente — sin consumidor aún (la SPA llega en Sprint 1); el gateway opera en el servidor (`127.0.0.1:8400`). Recomendado habilitarlo junto con la SPA.

---
**Cierre oficial de la plataforma base** y arranque de **Sprint 1** (Mis Servicios + Facturación) — ver `SPRINT_1_PLAN_COC.md`.

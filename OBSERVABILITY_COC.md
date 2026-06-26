# Observabilidad — Portal COC RC1 (logs, métricas, alertas)

## 1. Logs (estructurados)
- **Gateway:** JSON estructurado (structlog) con **`request_id`** de correlación por petición (middleware). Eventos de negocio: `request.start/end`, `auth_event` (login/refresh/logout/otp_*), `NEW LOGIN notify`.
- **Odoo (`sentinela_api`):** logger `sentinela.security` (creación de usuario portal, eventos de sesión efímera) + modelo `sentinela.coc.auth.log` (auditoría server-side consultable).
- **Regla de oro:** **nunca** se registran OTP, contraseñas ni api_key (número enmascarado). Verificado por test.

## 2. Métricas
- Endpoint **`/metrics`** (texto Prometheus) en el gateway:
  - `otp_send_total{result="ok|fail|circuit_open"}` — envíos OTP por resultado.
  - `otp_provider_up` (gauge 0/1) — disponibilidad del proveedor (EvoApi).
  - `otp_send_latency_ms_{last,avg,count}` — tiempos de respuesta del proveedor.
- **`/v1/providers/health`** — health del proveedor OTP (estado de la instancia WhatsApp).
- **`/health` / `/readyz`** — liveness/readiness del gateway.

## 3. Auditoría
- Gateway: `auth_audit_event` (login, refresh, refresh_reuse, logout, revoke, otp_*, password_*, phone_change*, magic_link_*). Expuesta al cliente vía `/v1/access-history`.
- Odoo: `sentinela.coc.auth.log` (apertura/cierre/expiración de sesión efímera, set_phone, secreto inválido).

## 4. Alertas recomendadas (a configurar en el monitoreo)
| Alerta | Condición | Severidad |
|---|---|---|
| Proveedor OTP caído | `otp_provider_up == 0` por > 2 min | 🔴 |
| Tasa de fallo OTP alta | `rate(otp_send_total{result="fail"}) ` elevado | 🟠 |
| Circuit breaker abierto | `otp_send_total{result="circuit_open"}` creciendo | 🟠 |
| Gateway no responde | `/health` != 200 | 🔴 |
| Pico de OTP/login fallidos | posible fuerza bruta (rate-limit disparándose) | 🟠 |
| Reuse de refresh detectado | `refresh_reuse` en auditoría | 🟠 (posible robo) |

## 5. Pendiente (post-RC)
- Tiempo real (WebSocket/SSE) para alarmas — Fase 4 del portal.
- Exportar métricas a Prometheus/Grafana del NOC; enganchar alertas a Telegram (ya usado en netwatch/monitoring).

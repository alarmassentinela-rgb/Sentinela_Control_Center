# OPERACIÓN 24×7 — Portal COC (manual de operación e incidencias)

> Guía de operación, monitoreo e incidentes de la plataforma base (WS-2 + WS-5 + EvoApi).
> Audiencia: NOC / soporte / on-call. Complementa `DEPLOY_RUNBOOK_COC_RC1.md` y `OBSERVABILITY_COC.md`.

## 1. Mapa rápido
| Pieza | Dónde | Cómo se ve |
|---|---|---|
| Gateway (FastAPI) | `api.sentinela.mx` (Docker, `/opt/sentinela_coc/gateway`) | `GET /health`, `/v1/providers/health`, `/metrics`, `/docs` |
| Addon Odoo `sentinela_api` | Odoo V18 (LAN) | rutas `/v1/*` y `/coc/internal/*` (solo LAN) |
| Proveedor OTP | EvoApi (`http://192.168.3.2:8080`, instancia `SentinelaWA`) | estado en `/v1/providers/health` |
| DB del gateway | Postgres dedicado (identidad/sesiones/auditoría) | — |
| Alertas | `infra/alerts/alert_checker.py` → Telegram (cron) | mensajes `[COC] …` |

## 2. Chequeo de salud (primero ante cualquier reporte)
```bash
curl -s api…/health                 # gateway vivo  -> {"status":"ok"}
curl -s api…/v1/providers/health    # proveedor OTP -> {"healthy":true}
curl -s api…/metrics | grep otp_    # métricas OTP / disponibilidad
```

## 3. Incidentes comunes y runbook

### 3.1 Clientes no reciben el OTP / no pueden entrar
1. `GET /v1/providers/health` → si `healthy:false` → **instancia WhatsApp caída**.
2. Verificar EvoApi: `curl -H "apikey:<key>" http://192.168.3.2:8080/instance/connectionState/SentinelaWA` → estado `open` esperado.
3. Si `close`/`connecting` → **reconectar la instancia** (escanear QR en el panel EvoApi).
4. Mientras tanto: el **login por contraseña** sigue disponible (fallback). Comunicar.
5. El circuit breaker se reabre solo cuando EvoApi responde; verás `otp_send_total{result="circuit_open"}` bajar.

### 3.2 Gateway no responde (`/health` ≠ 200)
1. `docker ps | grep gateway` y `docker logs --tail=100 <gateway>`.
2. `cd /opt/sentinela_coc/gateway && docker compose up -d` (o `restart`).
3. Verificar DB del gateway arriba (`gateway-db`).
4. Si persiste → rollback a imagen anterior (Runbook §6).

### 3.3 Odoo no responde / `/v1/me` falla
- Es problema de Odoo (núcleo). Revisar el servidor Odoo V18; el portal depende de él. Escalar a operación de Odoo.

### 3.4 Sospecha de abuso / fuerza bruta
- Picos de `otp_send_total{result="fail"}` o muchos 401: el rate-limit (IP/teléfono/dispositivo) ya bloquea. Revisar `auth_audit_event` (gateway) por IP. Si es ataque, bloquear IP en NPM/firewall.

### 3.5 Reporte de "me robaron la cuenta" / sesión sospechosa
- El cliente puede **cerrar todas las sesiones** desde el portal. Operación puede revocar vía DB del gateway (marcar `portal_session.revoked`). Forzar cambio de contraseña → revoca todo.
- `refresh_reuse` en auditoría = posible robo de token (la familia ya fue revocada automáticamente).

### 3.6 Cliente cambió de teléfono
- Flujo seguro en el portal (doble verificación). Si no puede, soporte actualiza el teléfono en Odoo (`res.partner`) y el cliente re-loguea por OTP.

## 4. Operaciones rutinarias
- **Reiniciar gateway:** `docker compose restart` (stateless; sesiones persisten en DB).
- **Reiniciar Odoo:** afecta a todos; la sesión efímera del portal persiste (FilesystemSessionStore).
- **Rotar secretos:** cambiar `COC_JWT_SECRET`/`COC_COC_SHARED_SECRET` (y el par en Odoo) → invalida sesiones/refresh (clientes re-loguean). Coordinar ventana.
- **Respaldos:** DB Odoo (cron 8h) + DB gateway (programar) + código en GitHub.

## 5. Escalamiento
| Severidad | Ejemplo | Acción |
|---|---|---|
| 🔴 Crítico | Gateway/Odoo caído; fuga de datos sospechada | On-call inmediato + (si fuga) revocar sesiones + revisar record rules |
| 🟠 Alto | Proveedor OTP caído; circuit breaker abierto | Reconectar WhatsApp; avisar fallback contraseña |
| 🟡 Medio | Latencia alta; fallos intermitentes | Revisar logs/métricas; abrir ticket |

## 6. Reglas de oro
- **Nunca** exponer `/coc/internal/*` a internet (solo LAN + secreto + allowlist).
- **Nunca** loguear OTP/contraseñas/secretos (ya garantizado por código).
- El aislamiento entre clientes lo dan las **record rules de Odoo**; ante cualquier cambio en seguridad, re-validar con pruebas negativas (A no ve datos de B).

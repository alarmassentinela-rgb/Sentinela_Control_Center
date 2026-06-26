# Smoke Tests — Portal COC RC1

> Pruebas rápidas de humo para STAGING (validación continua) y post-deploy en Producción.

## 1. Automatizadas (suites)
| Suite | Comando | Resultado actual (STAGING) |
|---|---|---|
| Gateway (unit) | `docker run --rm -v <gw>:/app -w /app coc-gateway:test python -m pytest -q` | **36/36** ✅ |
| Gateway (e2e real Odoo) | `... -e COC_E2E=1 -e COC_ODOO_BASE_URL=... -e COC_COC_SHARED_SECRET=... -e COC_E2E_MAP=... python -m pytest -q tests/test_e2e_staging.py` | **8/8** ✅ |
| Odoo seguridad | `odoo -d Sentinela_STAGING -u sentinela_api --test-enable --test-tags /sentinela_api --stop-after-init` | **19/19** ✅ |

## 2. Smoke post-deploy (manual/CLI)
```bash
# Gateway vivo
curl -s api…/health                      # {"status":"ok"}
curl -s api…/v1/providers/health         # {"provider":"evoapi","healthy":true}  (instancia WA conectada)
curl -s api…/metrics | head              # métricas Prometheus

# Auth real (requiere instancia WhatsApp conectada + número de prueba)
curl -s -X POST api…/v1/auth/otp/request -d '{"phone":"<test>","device":"smoke"}' -H 'Content-Type: application/json'
#   -> recibir OTP por WhatsApp en el número de prueba
curl -s -X POST api…/v1/auth/otp/verify  -d '{"phone":"<test>","code":"<otp>","device":"smoke"}' -H 'Content-Type: application/json'
#   -> {access_token, refresh_token}

# Aislamiento (record rules) con la sesión Odoo del login -> /v1/me devuelve SOLO el partner propio
```

## 3. Smoke de seguridad (aislamiento)
- Con dos clientes A y B: A no ve suscripciones/facturas/eventos/documentos de B (pruebas negativas). Ver `SECURITY_PENTEST_COC.md`.

## 4. Smoke real de OTP (PENDIENTE — gate de cierre de WS-5)
- Reconectar instancia `SentinelaWA` → `/v1/providers/health` healthy.
- Enviar OTP real a número de prueba → recibir → verificar → login OK.
- **Solo entonces** WS-5 queda cerrado al 100%.

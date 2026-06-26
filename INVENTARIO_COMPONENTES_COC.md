# Inventario de componentes, versiones y dependencias — Portal COC RC1

## 1. Componentes
| Componente | Ruta repo | Versión | Despliegue |
|---|---|---|---|
| `sentinela_api` (addon Odoo) | `/sentinela_api` | 18.0.0.1.0 | rsync → `-i/-u` en Odoo V18 (STAGING first) |
| COC Gateway (FastAPI) | `/sentinela_coc/gateway` | 0.2.0 | rsync → `docker compose up -d --build` |
| Alert checker | `/sentinela_coc/infra/alerts` | — | cron (python3 stdlib) |
| SPA Web (Next.js) | `/sentinela_coc/web` | — (Sprint 1) | Docker + NPM |

## 2. Dependencias — `sentinela_api` (manifest)
`base, web, portal, mail, sentinela_subscriptions, sentinela_monitoring, sentinela_fsm, sentinela_cfdi_prodigia, sentinela_digital_sign`
- Modelos propios: `sentinela.coc.auth.log`, `sentinela.coc.session.service` (abstract); extiende `res.users`.
- Seguridad: grupo `group_coc_portal` + record rules + ACL read-only.

## 3. Dependencias — Gateway (`requirements.txt`)
`fastapi>=0.115, uvicorn[standard]>=0.32, pydantic-settings>=2.5, httpx>=0.27, structlog>=24.4, python-jose[cryptography]>=3.3, passlib[argon2]>=1.7, pyotp>=2.9, psycopg[binary]>=3.2, sqlalchemy>=2.0, pytest>=8.3, pytest-asyncio>=0.24`
- Runtime: Python 3.12 (imagen `python:3.12-slim`).

## 4. Puertos / dominios
| Servicio | Puerto interno | Externo |
|---|---|---|
| Gateway | 8400 | `api.sentinela.mx` (Cloudflare + NPM) |
| SPA | (Next) | `portal.sentinela.mx` (Sprint 1) |
| Odoo V18 | 8069 | NO público (LAN; gateway en LAN) |
| EvoApi | 8080 | LAN |
| `/coc/internal/*` | (Odoo) | **NUNCA público** (LAN + secreto + allowlist) |

## 5. Configuración (toda por entorno / params — NUNCA en repo)
**Gateway (`COC_*`):** `LOG_LEVEL, ODOO_BASE_URL, COC_SHARED_SECRET, JWT_SECRET, JWT_ACCESS_TTL_MIN, JWT_REFRESH_TTL_DAYS, OTP_PROVIDER(mock|evoapi), OTP_TTL_SEC, OTP_MAX_ATTEMPTS, OTP_COOLDOWN_SEC, OTP_RATE_*, PASSWORD_MIN_LENGTH, GATEWAY_DB_URL, WA_BASE_URL, WA_API_KEY, WA_INSTANCE, WA_TIMEOUT_SEC, WA_RETRIES, WA_CB_*` (ver `.env.example`).
**Odoo (`ir.config_parameter`):** `sentinela_api.gateway_shared_secret`, `sentinela_api.coc_internal_allowed_cidrs`, `sentinela_monitoring.evoapi_url/key/instance`.

## 6. Secretos (ubicación)
- En Producción: vault / variables de entorno del contenedor. NUNCA en git.
- `JWT_SECRET`, `COC_SHARED_SECRET` (= `sentinela_api.gateway_shared_secret`), `WA_API_KEY` (= `sentinela_monitoring.evoapi_key`), credenciales DB gateway.
- `.gitignore` del monorepo excluye `.env`.

## 7. Datos / persistencia
- **Odoo (V18):** datos de negocio (fuente de verdad).
- **Gateway DB (Postgres):** identidad/sesiones/auditoría/magic links (NO datos de negocio).
- **Sesiones Odoo efímeras:** FilesystemSessionStore de Odoo (persisten reinicios).

## 8. Pruebas (cobertura)
- Gateway: 36 unit (pytest) + 8 e2e (real Odoo) + 1 micro-bench.
- Odoo `sentinela_api`: 19 (TransactionCase, incl. aislamiento/seguridad).
- PenTest: 6 probes activos.

# sentinela_coc — Monorepo del Centro de Operaciones del Cliente

Monorepo del Portal COC de Sentinela (decisión aprobada: monorepo gateway + SPA + infra).

```
sentinela_coc/
├── gateway/   API Gateway / BFF (FastAPI): identidad/OTP/JWT, agregación, caché, ruteo notif.
├── web/       SPA del portal (Next.js) — se inicializa en Sprint 1.
├── infra/     Docker Compose, despliegue (Cloudflare/NPM), observabilidad.
└── docs/      OpenAPI, runbooks, observabilidad.
```

## Componentes y dominios
- **Gateway** → `api.sentinela.mx` (FastAPI + Docker). Único que habla con Odoo (`sentinela_api`) en LAN.
- **Web (SPA)** → `portal.sentinela.mx` (Next.js + Docker). Consume solo el gateway.
- **Almacén propio del gateway:** Postgres dedicado (`portal_identity`/OTP/sesiones). NO datos de negocio (esos viven en Odoo).

## Principios
- Odoo = fuente de verdad. El gateway NO duplica lógica ni datos de negocio.
- **Seguridad:** record rules de Odoo = primera línea de defensa (usuario portal lazy). El gateway las complementa, nunca las sustituye.
- **Observabilidad desde el inicio:** OpenAPI/Swagger (`/docs`), logging estructurado JSON con `request_id`, healthchecks (`/health`, `/readyz`), métricas.
- **Pruebas desde el inicio:** unitarias, integración, seguridad, smoke (ver `gateway/tests/`).

## Estado
Sprint 0 — base del gateway (health, settings, logging, OpenAPI). Identidad/OTP/JWT = WS-5. SPA = Sprint 1.

## Deploy (standalone, NO usa skills de Odoo)
`rsync` al server + `docker compose up -d --build`. STAGING primero. Ver `infra/`.

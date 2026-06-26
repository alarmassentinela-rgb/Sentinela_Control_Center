# sentinela_api — Capa REST/JSON del Portal COC

Addon Odoo 18 que expone los módulos `sentinela_*` al **Centro de Operaciones del Cliente** (portal web + app móvil), consumido a través del **Gateway** (`sentinela_coc/gateway`).

> **Principio:** NO duplica lógica de negocio. Cada endpoint invoca métodos de modelo existentes (`_render_master_report_pdf`, `get_last_location_from_traccar`, `register_survey_response`, `action_sign`, …) y serializa. Ver `DOC_TECNICO_IMPLEMENTACION_COC.md`.

## Estado
Sprint 0 — **esqueleto**: `GET /v1/me` (auth usuario portal) y `GET /v1/config/theme` (público, costura de branding). Seguridad (record rules + ACL) y recursos de negocio se agregan en los siguientes work-streams.

## Estructura
```
controllers/   main.py (base: API_PREFIX, json_ok, problem RFC-7807) · me.py · config.py
lib/           serializers.py (DTO estables) · (scoping.py en WS-2)
security/      portal_security.xml + ir.model.access.csv (WS-2)
tests/         test_smoke.py (WS-7)
```

## Convenciones
- Prefijo `/v1`. Respuestas con `X-Request-Id` (trazabilidad WS-8). Errores RFC-7807 (`problem()`).
- **Scoping:** record rules de Odoo (usuario portal lazy, Opción A) = primera línea de defensa. El gateway corre como el usuario portal; nunca sustituye las rules.
- **Serializar explícito**, no `read()` crudo: el contrato no se rompe si cambia un modelo.

## Cómo agregar un recurso
1. Crear `controllers/<recurso>.py` con `@http.route(API_PREFIX + '/...')`.
2. Invocar el método de modelo existente (no reimplementar lógica).
3. Serializar en `lib/serializers.py`.
4. Agregar test en `tests/`.

## Deploy
Server NO es git tree. Usar skills `release-modulo` → `deploy-modulo` (rsync → `-u` STAGING → `-u` V18 → verificar). **STAGING primero.**

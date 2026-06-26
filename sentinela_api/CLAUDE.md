# sentinela_api

Capa **REST/JSON** del Portal COC (Centro de Operaciones del Cliente). Expone los módulos `sentinela_*` al portal web y a la app móvil, a través del **Gateway** (`sentinela_coc/gateway`). **NO duplica lógica de negocio**: invoca métodos de modelo existentes y serializa.

> Documenta el **cómo es el código**. El estado/decisiones del proyecto vive en memoria (`project_portal_coc`) y en los docs del repo (`PRD_PORTAL_COC_SENTINELA.md`, `DOC_TECNICO_IMPLEMENTACION_COC.md`).

- **Versión:** ver `__manifest__.py` (hoy `18.0.0.1.0`, esqueleto Sprint 0).
- **Odoo:** 18 Community. **DB prod:** V18 · **DB lab:** Sentinela_STAGING (`:8075`).
- **Deploy:** skills `release-modulo` → `deploy-modulo`. STAGING primero (server no es git tree).

## Dependencias (manifest)
`base, web, portal, mail, sentinela_subscriptions, sentinela_monitoring, sentinela_fsm, sentinela_cfdi_prodigia, sentinela_digital_sign`.

## Arquitectura
- **controllers/**: un archivo por recurso. `main.py` = base (`API_PREFIX='/v1'`, `json_ok`, `problem` RFC-7807, `get_request_id`).
- **lib/**: `serializers.py` (DTO estables — serializar explícito, NO `read()` crudo). `scoping.py` (helper de filtro, WS-2).
- **security/** (WS-2): grupo Portal + **record rules** por partner (PRIMERA línea de defensa, Opción A: usuario portal lazy) + ACL read-only.
- **tests/**: `TransactionCase` (WS-7). Los tests de aislamiento (TC-S1..S4) son obligatorios antes de exponer cada recurso.

## Trampas / reglas
- El scoping por cliente lo garantizan **record rules de Odoo**, no el gateway. Todo recurso debe verificarse con test de aislamiento negativo (cliente A no ve datos de B).
- `auth='user'` en recursos privados (corre como usuario portal); `auth='public'` solo en theme y magic links.
- No meter lógica de negocio aquí: si falta un método, se **extrae** al módulo dueño (p. ej. `create_from_customer_request` en fsm), no se reimplementa.

## Estado actual
Esqueleto: `GET /v1/me`, `GET /v1/config/theme`. Pendiente WS-2 (seguridad), WS-3 (auditoría), recursos de negocio (Sprint 1+).

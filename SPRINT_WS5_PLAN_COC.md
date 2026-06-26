# WS-5 — Gateway de identidad (OTP WhatsApp + JWT) · Plan

> Plan previo a codificar. Se desarrolla y valida **100% en STAGING** (no depende de Producción).
> Metodología por Sprints. Referencias: `PRD_PORTAL_COC_SENTINELA.md` §3/§5, `DOC_TECNICO_IMPLEMENTACION_COC.md` §4.1, `SECURITY_PORTAL_COC.md`.
> Escala: `XS`≈½d · `S`≈1d · `M`≈2-3d · `L`≈4-5d. Estimado total: **~30–40 pts (≈ 2–2.5 sem)**.

## 1. Objetivo
Construir la identidad del Portal: el cliente entra con **OTP por WhatsApp** (o contraseña/biométrico), el Gateway emite **JWT**, y **opera contra Odoo COMO el usuario portal del cliente** (vía API key de `res.users`) para que las **record rules de WS-2 sean la primera línea de defensa real**. Criterio de éxito: login con WhatsApp en STAGING → JWT → `GET /v1/me` con datos propios; un token de A jamás ve datos de B (aunque se manipule).

## 2. Alcance
**DENTRO:**
- Store `portal_identity` (Postgres del gateway): teléfono/email → partner_id.
- OTP por WhatsApp (driver EvoApi, canal transaccional) + rate-limit + bloqueo.
- JWT (access + refresh) + login por contraseña (argon2) + registro de credencial biométrica.
- Recuperación (WhatsApp/email).
- **Handshake con Odoo:** endpoint protegido que asegura el usuario portal lazy (WS-2) y entrega una **API key** del usuario; el Gateway llama a Odoo con esa key (corre como el portal).
- `GET /v1/me` y `GET /v1/config/theme` end-to-end a través del Gateway.
- OpenAPI/Swagger, logging estructurado, métricas, smoke.
- Pruebas: unitarias (OTP/JWT), integración (gateway↔Odoo), **seguridad** (un token no cruza clientes), smoke.

**FUERA:** recursos de negocio (Sprint 1), SPA completa (solo cliente HTTP/Postman + shell mínimo opcional), despliegue a Producción.

## 3. Decisión técnica clave (handshake de identidad)
El Gateway **no** usa una cuenta de servicio con `with_user`. Tras verificar identidad:
1. Llama a un endpoint **interno** de `sentinela_api` (auth por secreto compartido gateway↔Odoo) con el `partner_id` verificado.
2. Odoo ejecuta `res.users._coc_ensure_portal_user(partner)` (WS-2) y **genera/devuelve una API key** de ese usuario portal.
3. El Gateway guarda la referencia y hace las llamadas siguientes con esa API key → **Odoo corre como el usuario portal → aplican las record rules**.
Así el aislamiento NO depende del Gateway; el Gateway solo decide *quién* eres, no *qué ves*.

## 4. Tareas, orden y complejidad
| ID | Tarea | Complej. | Dep. |
|---|---|---|---|
| W5.1 | Store `portal_identity` + migraciones (SQLAlchemy) en Postgres del gateway | S | — |
| W5.2 | Driver de mensajería WhatsApp (interfaz + EvoApi) para OTP | M | — |
| W5.3 | Flujo OTP: `request`/`verify` + TTL + rate-limit + bloqueo por intentos | M | W5.1, W5.2 |
| W5.4 | JWT access+refresh (emisión/rotación/expiración/logout) | M | W5.1 |
| W5.5 | Login por contraseña (argon2) + recuperación (WhatsApp/email) + biométrico (registro) | M | W5.4 |
| W5.6 | **Odoo:** endpoint interno `ensure-portal-session` (auth secreto) → usuario lazy + **API key** | M | (WS-2 ✅) |
| W5.7 | **Handshake** gateway↔Odoo: obtener/guardar API key del portal; cliente Odoo que llama como el portal | M | W5.6 |
| W5.8 | `GET /v1/me` y `/v1/config/theme` end-to-end vía gateway (con scope real) | S | W5.7 |
| W5.9 | OpenAPI/Swagger + logging estructurado + `/metrics` + healthchecks | S | W5.4 |
| W5.10 | Pruebas: unit (OTP/JWT), integración (E2E login→/me), **seguridad** (token A no ve B), smoke | M | W5.8 |
| W5.11 | Despliegue del gateway a STAGING (docker compose) + smoke post-deploy | S | W5.10 |

**Orden:** W5.1 → (W5.2 ∥ W5.4) → W5.3 → W5.5 → W5.6 → W5.7 → W5.8 → W5.9 → W5.10 → W5.11.
**Ruta crítica:** W5.6 → W5.7 → W5.8 (handshake) — es lo que conecta identidad con el aislamiento de WS-2.

## 5. Entregables
- Gateway con OTP WhatsApp + JWT operando en STAGING.
- Endpoint interno de handshake + API key del portal en `sentinela_api`.
- `/v1/me` y `/v1/config/theme` end-to-end con scope real.
- OpenAPI publicado, logs estructurados, métricas.
- Suite de pruebas (unit/integración/seguridad/smoke) verde.
- Doc: `gateway/README.md`, actualización de `SECURITY_PORTAL_COC.md` (capa auth).

## 6. Dependencias
- EvoApi (WhatsApp) con sesión/plantilla apta para OTP (validar early, W5.2).
- `sentinela_api` instalado en STAGING (✅ WS-2).
- Postgres del gateway (docker-compose ya scaffolded).
- Secreto compartido gateway↔Odoo (en `ir.config_parameter`/env/vault).

## 7. Riesgos
| Riesgo | Sev. | Mitigación |
|---|---|---|
| EvoApi no apto para OTP (plantillas/sesión) | 🟠 | Validar en W5.2; fallback contraseña; SMS plan B futuro |
| Suplantación de `partner_id` en el handshake | 🔴 | Endpoint interno con secreto compartido + solo LAN; el `partner_id` lo fija Odoo tras verificar OTP, no el cliente |
| Fuga de API keys del portal | 🟠 | Guardar cifradas/solo referencia; rotación; alcance mínimo |
| Fuerza bruta OTP | 🟠 | Rate-limit + bloqueo + expiración corta |
| 43% de subs sin teléfono | 🟡 | Campaña de captura en paralelo; permitir alta de contraseña/email |

## 8. Casos de prueba
- OTP: correcto→JWT; incorrecto/expirado→rechazo; N intentos→bloqueo+rate-limit.
- JWT: refresh rota; access expira; logout invalida.
- Teléfono no registrado → mensaje neutro (no filtra existencia).
- Handshake: crea usuario portal lazy idempotente; API key válida; Gateway llama como portal.
- **Seguridad (clave):** con el JWT/clave de A, `GET /v1/me` y futuros recursos devuelven SOLO datos de A; manipular IDs no expone a B (las record rules de WS-2 lo impiden).
- Smoke post-deploy: `/health`, login, `/v1/me`.

## 9. Criterios de aceptación
- ✅ Login WhatsApp end-to-end en STAGING → JWT → `/v1/me` con datos propios.
- ✅ El Gateway opera como el usuario portal (record rules aplican); token de A no ve datos de B.
- ✅ Suite unit/integración/seguridad/smoke verde.
- ✅ OpenAPI + logs estructurados + healthchecks activos.
- ✅ Validado en STAGING (no requiere Producción).

## 10. Plan de rollback
- Gateway stateless en Docker: rollback = imagen anterior (`docker compose` al tag previo).
- `portal_identity`: respaldo del Postgres del gateway antes de migraciones.
- Endpoint interno en `sentinela_api`: aditivo; rollback = revertir commit + `-u` en STAGING.
- No toca datos de negocio de Odoo.

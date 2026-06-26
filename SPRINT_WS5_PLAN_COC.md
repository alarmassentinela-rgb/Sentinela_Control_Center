# WS-5 — Gateway de identidad (OTP + sesiones cortas) · Plan

> Plan de WS-5. Se desarrolla y valida **100% en STAGING** (no depende de Producción).
> Principio: **Gateway = identidad; Odoo = autorización (record rules de WS-2).**
> Ajuste aprobado: **sin credenciales permanentes ni API keys**. Sesiones de **vida corta** + refresh rotativo + revocación.
> Escala: `XS`≈½d · `S`≈1d · `M`≈2-3d · `L`≈4-5d. Estimado: **~38–48 pts (≈ 2.5–3 sem)**.

## 1. Objetivo
El cliente se autentica por **OTP WhatsApp** (o contraseña/biométrico); el Gateway emite una **sesión de vida corta** (access JWT corto + refresh rotativo) y opera contra Odoo **como el usuario portal lazy mediante una sesión Odoo efímera** (no API key). Desde el inicio: auditoría de autenticación, gestión de dispositivos/sesiones, rate limiting y magic links de un solo uso. Éxito: login WhatsApp en STAGING → sesión corta → `/v1/me` con datos propios; revocable; un token de A jamás ve datos de B.

## 2. Alcance
**DENTRO:**
- Identidad: `portal_identity` (teléfono/email → partner_id).
- **OTP WhatsApp** (driver EvoApi, canal transaccional) — request/verify.
- **Sesiones cortas:** access JWT corto + **refresh token independiente y rotativo** + **revocación** + **"cerrar todas las sesiones"**.
- **Sesión Odoo efímera** del usuario portal lazy (handshake, §3) — sin credenciales permanentes.
- **Auditoría de autenticación completa** (todos los eventos).
- **Gestión de dispositivos y sesiones activas** (listar/cerrar).
- **Rate limiting** en login, OTP (request/verify) y refresh.
- **Magic links de un solo uso** (firma/autorizaciones).
- Login por contraseña (argon2) + biométrico (registro) + recuperación.
- `GET /v1/me`, `/v1/config/theme` end-to-end vía gateway.
- OpenAPI/Swagger, logging estructurado, métricas, smoke.
- Pruebas: unit, integración, **seguridad**, smoke.

**FUERA:** recursos de negocio (Sprint 1), SPA completa (cliente HTTP/Postman + shell mínimo opcional), Producción.

## 3. Diseño de autenticación (sesiones de vida corta, SIN API keys)
**El Gateway es la fuente de verdad de la sesión del cliente:**
- `portal_session`: 1 fila por sesión (device, ip, user-agent, created, last_seen, expires, refresh_hash, refresh_family, revoked).
- **Access token:** JWT **corto** (~15 min), firma del gateway; claims: `sid` (jti de sesión), `partner_id`, `odoo_uid`, `exp`.
- **Refresh token:** opaco, **independiente y rotativo** (rota en cada uso; TTL ~30 d; guardado **hasheado**). Detección de **reuse** → revoca toda la familia (token theft).
- **Revocación:** marcar `revoked` (el access deja de validar por `sid`; el refresh deja de rotar). **Cerrar todas las sesiones** = revocar todas las del partner.

**Autorización = Odoo (record rules de WS-2), vía sesión Odoo efímera:**
- Endpoint interno `POST /coc/internal/session` en `sentinela_api` (auth por **secreto compartido** gateway↔Odoo, solo LAN): `_coc_ensure_portal_user(partner)` + **abre una sesión Odoo de vida corta** (uid + session_token) → devuelve `session_id` efímero. **No API key.**
- El Gateway usa ese `session_id` como el usuario portal → **aplican las record rules**. Se **renueva** al refrescar el access; se **destruye** al revocar/cerrar sesión. `session_lifetime` de Odoo en valor corto.
- El `partner_id` lo fija **Odoo** tras la verificación OTP del Gateway; el cliente nunca lo envía.

## 4. Tareas, orden y complejidad
| ID | Tarea | Complej. | Dep. |
|---|---|---|---|
| W5.1 | **Capa de datos** del gateway (SQLAlchemy): `portal_identity`, `portal_session`, `otp_challenge`, `auth_audit_event`, `magic_link_token` | M | — |
| W5.2 | Driver de mensajería WhatsApp (interfaz + EvoApi) para OTP | M | — |
| W5.3 | OTP request/verify (TTL, single-use) + **rate limit OTP** | M | W5.1, W5.2 |
| W5.4 | **Sesiones cortas:** emisión access JWT corto + refresh rotativo + verificación/rotación + **detección de reuse** | M | W5.1 |
| W5.5 | **Revocación**: logout, revocar sesión, **cerrar todas las sesiones** | S | W5.4 |
| W5.6 | **Odoo:** endpoint interno `open/close session` (secreto compartido) → usuario lazy + **sesión Odoo efímera** | M | (WS-2 ✅) |
| W5.7 | **Handshake** gateway↔Odoo: abrir/renovar/cerrar sesión Odoo ligada a la sesión del gateway | M | W5.6 |
| W5.8 | Login contraseña (argon2) + recuperación (WhatsApp/email) + biométrico (registro) + **rate limit login/refresh** | M | W5.4 |
| W5.9 | **Auditoría de autenticación** (todos los eventos) + **gestión de dispositivos/sesiones** (listar/cerrar) | M | W5.1, W5.4 |
| W5.10 | **Magic links de un solo uso** (firma/autorizaciones) | S | W5.1 |
| W5.11 | `GET /v1/me` y `/v1/config/theme` end-to-end vía gateway (scope real) | S | W5.7 |
| W5.12 | OpenAPI + logging estructurado + `/metrics` + healthchecks | S | W5.4 |
| W5.13 | Pruebas unit/integración/**seguridad**/smoke | M | W5.11 |
| W5.14 | Despliegue del gateway a STAGING + smoke post-deploy | S | W5.13 |

**Orden:** W5.1 → (W5.2 ∥ W5.4) → W5.3 → W5.5 → W5.6 → W5.7 → W5.8 → W5.9/W5.10 → W5.11 → W5.12 → W5.13 → W5.14.
**Ruta crítica:** W5.6 → W5.7 → W5.11 (sesión Odoo efímera = puente identidad↔autorización).

## 5. Entregables
- Gateway con OTP WhatsApp + **sesiones cortas** (access/refresh/revocación/cerrar-todas) en STAGING.
- Endpoint interno de sesión Odoo efímera en `sentinela_api` (sin API keys).
- Auditoría de autenticación + gestión de dispositivos/sesiones.
- Rate limiting (login/OTP/refresh) + magic links de un solo uso.
- `/v1/me` end-to-end con scope real; OpenAPI + logs + métricas.
- Suite de pruebas verde. Doc: `gateway/README.md`, update `SECURITY_PORTAL_COC.md`.

## 6. Dependencias
- EvoApi (WhatsApp) apta para OTP (validar early, W5.2).
- `sentinela_api` instalado en STAGING (✅ WS-2).
- Postgres del gateway (scaffolded). Redis opcional para rate limit (si no, tabla/contadores).
- Secreto compartido gateway↔Odoo (`ir.config_parameter`/env/vault).

## 7. Riesgos
| Riesgo | Sev. | Mitigación |
|---|---|---|
| EvoApi no apto para OTP | 🟠 | Validar W5.2; fallback contraseña; SMS plan B |
| Robo de refresh token | 🟠 | Rotación + detección de reuse → revoca familia; hash en DB |
| Suplantación de `partner_id` en handshake | 🔴 | Secreto compartido + solo LAN; partner_id lo fija Odoo tras OTP |
| Sesión Odoo huérfana/larga | 🟡 | `session_lifetime` corto; cierre al revocar; renovación ligada al access |
| Fuerza bruta login/OTP | 🟠 | Rate limit + bloqueo + expiración corta |
| 43% subs sin teléfono | 🟡 | Captura en paralelo; permitir contraseña/email |

## 8. Casos de prueba
- OTP: ok→sesión; incorrecto/expirado/reusado→rechazo; exceso→rate limit/bloqueo.
- Sesión: access expira pronto; refresh rota; **reuse de refresh → revoca familia**; logout invalida; **cerrar-todas** invalida todas.
- Handshake: usuario portal lazy idempotente; sesión Odoo efímera válida; al cerrar sesión gateway → sesión Odoo destruida.
- **Seguridad (clave):** con sesión de A, `/v1/me` y recursos devuelven SOLO datos de A; manipular IDs no expone a B (record rules WS-2).
- Auditoría: cada evento queda registrado (partner, ip, ua, device, resultado).
- Dispositivos/sesiones: listar y cerrar una/todas.
- Magic link: un solo uso; segundo intento rechazado; expira.
- Rate limit: login/OTP/refresh bloquean tras N intentos.
- Smoke: `/health`, login, `/v1/me`.

## 9. Criterios de aceptación
- ✅ Login WhatsApp end-to-end en STAGING → sesión corta → `/v1/me` propio.
- ✅ Refresh rotativo + revocación + cerrar-todas funcionan; reuse detectado.
- ✅ Gateway opera como usuario portal (record rules aplican); token de A no ve datos de B.
- ✅ Auditoría, gestión de dispositivos/sesiones, rate limiting y magic links de un solo uso operativos.
- ✅ OpenAPI + logs estructurados + healthchecks; suite verde; validado en STAGING.

## 10. Plan de rollback
- Gateway stateless en Docker: rollback = imagen anterior.
- DB del gateway: respaldo antes de migraciones; migraciones reversibles.
- Endpoint interno en `sentinela_api`: aditivo; rollback = revertir commit + `-u` STAGING.
- No toca datos de negocio de Odoo.

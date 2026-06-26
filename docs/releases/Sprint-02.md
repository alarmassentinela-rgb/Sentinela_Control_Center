# Sprint-02 — Gateway de Identidad: OTP + sesiones cortas (WS-5)

**Fechas:** 2026-06-26 → (en curso) · **Estado:** 🚧 En curso

## Objetivo
Construir la identidad del Portal: el cliente se autentica por **OTP WhatsApp** (o contraseña/biométrico), el Gateway emite una **sesión de vida corta** y opera contra Odoo **como el usuario portal lazy mediante una sesión Odoo efímera** (sin credenciales permanentes). Principio: **Gateway = identidad; Odoo = autorización (record rules de WS-2).**

## Cambios
- **Plan WS-5** revisado al modelo aprobado: **sin API keys**; access JWT corto + **refresh rotativo** (detección de reuse → revoca familia) + **revocación** + **cerrar todas las sesiones**; **auditoría de auth**, **gestión de dispositivos/sesiones**, **rate limiting** (login/OTP/refresh), **magic links de un solo uso**.
- **W5.1 — Capa de datos del Gateway** (SQLAlchemy): `portal_identity`, `portal_session` (access_jti, refresh hash+familia rotativo, `odoo_session_id` efímero, device/ip/ua, revocación), `otp_challenge` (single-use), `auth_audit_event`, `magic_link_token` (un solo uso).
- **W5.6 — Handshake (sesión Odoo efímera, sin API keys):** servicio `sentinela.coc.session.service` (open/check/close) + endpoints internos `/coc/internal/session/*` protegidos por **secreto compartido** (fail-closed) + **auditoría server-side** (`sentinela.coc.auth.log`) + **hardening de concurrencia** del usuario portal lazy (savepoint + IntegrityError → re-search). **Base oficial de autenticación** validada dinámicamente en STAGING.

## Commits
| Hash | Fecha | Descripción |
|---|---|---|
| `c5ea76b` | 26-jun | docs: ... + **plan WS-5 (gateway identidad OTP/JWT)** |
| `5b4bc1a` | 26-jun | feat(coc): WS-5 plan (sesiones cortas, sin API keys) + **W5.1 capa de datos gateway** |
| `4bf6c19` | 26-jun | feat(coc): **W5.6 handshake** — sesión Odoo efímera del usuario portal (sin API keys) |

## Riesgos
- 🔴 Suplantación de `partner_id` en el handshake → mitigación: endpoint interno con **secreto compartido**, solo LAN; el `partner_id` lo fija Odoo tras la verificación OTP.
- 🟠 Robo de refresh token → rotación + detección de reuse (revoca familia) + hash en DB.
- 🟡 Sesión Odoo efímera huérfana → `session_lifetime` corto + cierre al revocar.
- 🟠 EvoApi (WhatsApp) apto para OTP → validar temprano (W5.2); fallback contraseña.
- ⚠️ **Punto técnico a des-riesgar (próximo):** abrir/usar/cerrar una sesión Odoo programática como el usuario portal (W5.6/W5.7) — validar dinámicamente en STAGING, como se hizo en WS-2.

## Pruebas
- **W5.6 — validación dinámica en STAGING (ruta HTTP real :8075).** Garantías del modelo de confianza:

| Garantía | Resultado |
|---|---|
| G1 La sesión representa al usuario portal correcto | ✅ `/v1/me` devuelve el partner correcto |
| G2 Sin credenciales permanentes (no API keys) | ✅ sesión Odoo efímera con token ligado al sid |
| G3 Revocación inmediata | ✅ tras `close`, `/v1/me` → 303 (sin datos) |
| G4 Expiración automática | ✅ ttl=0 → `check` expired (GC lazy) |
| G5 Respeta record rules (WS-2) | ✅ A ve 1 sub (no 242); IDOR a sub de B denegado |
| G6 Sin escalada de privilegios | ✅ `ir.config_parameter` denegado al portal |
| G7 Auditoría completa | ✅ `sentinela.coc.auth.log` (18 eventos) |
| G8 Cierre sin recursos abiertos | ✅ `check` post-close → not_found |
| G9 Seguro ante reinicio de Odoo | ✅ sesión persiste tras `docker restart` |

  Escenarios de error: partner inexistente ✅ · usuario deshabilitado ✅ · partner sin usuario portal (lazy) ✅ · sesión expirada ✅ · secreto inválido (forbidden) ✅ · intentos repetidos ✅ · **concurrentes (5 opens → 1 usuario)** ✅.
- **Suite automatizada:** 19/19 verde (incluye `test_coc_session`). Reinicio del Gateway: cubierto por diseño (el `odoo_session_id` vive en `portal_session`, gateway stateless).

## Bugs
- Ninguno en la lógica. (Nota: un falso-fallo inicial del Bloque 3 fue **timing del harness** —odoo-lab aún cargaba tras el restart—; resuelto con espera robusta `--retry-all-errors`.)

## Rollback
- Gateway stateless en Docker: rollback = imagen anterior.
- DB del Gateway: respaldo antes de migraciones; migraciones reversibles.
- Endpoint interno en `sentinela_api`: aditivo; revertir commit + `-u` STAGING.
- No toca datos de negocio de Odoo.

## Estado
🚧 **En curso.** Hecho: plan revisado + W5.1 (capa de datos) + **W5.6 handshake validado en STAGING** (base oficial de autenticación). Siguiente: **W5.2/W5.3** (driver WhatsApp + OTP) → **W5.4/W5.5** (sesiones cortas access/refresh + revocación/cerrar-todas) → W5.8 (login/recuperación) → W5.9/W5.10 (auditoría/dispositivos + magic links). Se desarrolla y valida 100% en STAGING.

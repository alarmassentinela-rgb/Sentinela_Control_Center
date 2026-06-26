# Sprint-02 — Gateway de Identidad: OTP + sesiones cortas (WS-5)

**Fechas:** 2026-06-26 → (en curso) · **Estado:** 🚧 En curso

## Objetivo
Construir la identidad del Portal: el cliente se autentica por **OTP WhatsApp** (o contraseña/biométrico), el Gateway emite una **sesión de vida corta** y opera contra Odoo **como el usuario portal lazy mediante una sesión Odoo efímera** (sin credenciales permanentes). Principio: **Gateway = identidad; Odoo = autorización (record rules de WS-2).**

## Cambios
- **Plan WS-5** revisado al modelo aprobado: **sin API keys**; access JWT corto + **refresh rotativo** (detección de reuse → revoca familia) + **revocación** + **cerrar todas las sesiones**; **auditoría de auth**, **gestión de dispositivos/sesiones**, **rate limiting** (login/OTP/refresh), **magic links de un solo uso**.
- **W5.1 — Capa de datos del Gateway** (SQLAlchemy): `portal_identity`, `portal_session` (access_jti, refresh hash+familia rotativo, `odoo_session_id` efímero, device/ip/ua, revocación), `otp_challenge` (single-use), `auth_audit_event`, `magic_link_token` (un solo uso).

## Commits
| Hash | Fecha | Descripción |
|---|---|---|
| `c5ea76b` | 26-jun | docs: ... + **plan WS-5 (gateway identidad OTP/JWT)** |
| `5b4bc1a` | 26-jun | feat(coc): WS-5 plan (sesiones cortas, sin API keys) + **W5.1 capa de datos gateway** |

## Riesgos
- 🔴 Suplantación de `partner_id` en el handshake → mitigación: endpoint interno con **secreto compartido**, solo LAN; el `partner_id` lo fija Odoo tras la verificación OTP.
- 🟠 Robo de refresh token → rotación + detección de reuse (revoca familia) + hash en DB.
- 🟡 Sesión Odoo efímera huérfana → `session_lifetime` corto + cierre al revocar.
- 🟠 EvoApi (WhatsApp) apto para OTP → validar temprano (W5.2); fallback contraseña.
- ⚠️ **Punto técnico a des-riesgar (próximo):** abrir/usar/cerrar una sesión Odoo programática como el usuario portal (W5.6/W5.7) — validar dinámicamente en STAGING, como se hizo en WS-2.

## Pruebas
- W5.1: validación de sintaxis (`py_compile`). Las pruebas funcionales (OTP, sesiones, reuse, handshake, aislamiento end-to-end, rate limit, magic link single-use) se ejecutarán al implementar W5.3+ en STAGING.

## Bugs
- Ninguno aún (capa de datos recién creada).

## Rollback
- Gateway stateless en Docker: rollback = imagen anterior.
- DB del Gateway: respaldo antes de migraciones; migraciones reversibles.
- Endpoint interno en `sentinela_api`: aditivo; revertir commit + `-u` STAGING.
- No toca datos de negocio de Odoo.

## Estado
🚧 **En curso.** Hecho: plan revisado + W5.1 (capa de datos). Siguiente: **W5.6** (sesión Odoo efímera — des-riesgo del handshake) → W5.2/W5.3 (OTP) → W5.4/W5.5 (sesiones/revocación). Se desarrolla y valida 100% en STAGING.

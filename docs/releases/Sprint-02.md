# Sprint-02 — Gateway de Identidad: OTP + sesiones cortas (WS-5)

**Fechas:** 2026-06-26 → (en curso) · **Estado:** 🚧 En curso

## Objetivo
Construir la identidad del Portal: el cliente se autentica por **OTP WhatsApp** (o contraseña/biométrico), el Gateway emite una **sesión de vida corta** y opera contra Odoo **como el usuario portal lazy mediante una sesión Odoo efímera** (sin credenciales permanentes). Principio: **Gateway = identidad; Odoo = autorización (record rules de WS-2).**

## Cambios
- **Plan WS-5** revisado al modelo aprobado: **sin API keys**; access JWT corto + **refresh rotativo** (detección de reuse → revoca familia) + **revocación** + **cerrar todas las sesiones**; **auditoría de auth**, **gestión de dispositivos/sesiones**, **rate limiting** (login/OTP/refresh), **magic links de un solo uso**.
- **W5.1 — Capa de datos del Gateway** (SQLAlchemy): `portal_identity`, `portal_session` (access_jti, refresh hash+familia rotativo, `odoo_session_id` efímero, device/ip/ua, revocación), `otp_challenge` (single-use), `auth_audit_event`, `magic_link_token` (un solo uso).
- **W5.6 — Handshake (sesión Odoo efímera, sin API keys):** servicio `sentinela.coc.session.service` (open/check/close) + endpoints internos `/coc/internal/session/*` protegidos por **secreto compartido** (fail-closed) + **auditoría server-side** (`sentinela.coc.auth.log`) + **hardening de concurrencia** del usuario portal lazy (savepoint + IntegrityError → re-search). **Base oficial de autenticación** validada dinámicamente en STAGING.
- **W5.2 — Proveedor OTP DESACOPLADO:** interfaz `OtpProvider` + `MockOtpProvider` (dev/test) + `EvoApiOtpProvider` (stub, se cablea por config). Cliente Odoo desacoplado (`HttpOdooClient` + `FakeOdooClient`).
- **W5.3 — Flujo OTP completo:** OTP **solo como hash** (pepper), **TTL 5 min**, **3 intentos**, **cooldown**, **rate limiting por IP/teléfono/dispositivo**, **auditoría completa**. Endpoints `/v1/auth/otp/request|verify`.
- **W5.4 (parcial) — Sesiones cortas:** access JWT corto + **refresh rotativo de un solo uso** con **detección de reuse** (revoca familia) + `/refresh` + `/logout`. Autorización sigue en Odoo (sesión efímera del handshake).
- **W5.7 — E2E Gateway↔Odoo con datos reales (STAGING):** endpoint Odoo `/coc/internal/identity/resolve` (teléfono→partner); `HttpOdooClient` real cableado; **refresh endurecido contra concurrencia** (claim atómico `UPDATE..WHERE used=false`). EvoApi sigue intercambiable (Mock OTP en pruebas).
- **Integración EvoApi (proveedor OTP real):** driver `otp_evoapi` intercambiable por config (`COC_OTP_PROVIDER=evoapi`) con **health check**, **reintentos controlados**, **circuit breaker** (closed/open/half-open), **manejo seguro de errores**, **timeout**; normaliza el número a E.164 sin `+`; **nunca loguea OTP ni api_key** (número enmascarado); **métricas** (disponibilidad/latencia) en `/metrics` (Prometheus) + `/v1/providers/health`. Toda la config por entorno (fuera del código).
- **W5.8 — sistema de identidad (contraseñas):** **Argon2** (passlib) + **política** (longitud/letras+dígitos/no repetitiva); **cambio de contraseña** (verifica la actual); **login por contraseña**; **recuperación por OTP**; **cambio seguro de teléfono con doble verificación** (OTP a teléfono nuevo + actual); **revocación de TODAS las sesiones al cambiar credenciales**; auditoría completa. Biometría = responsabilidad del dispositivo/navegador (el Gateway solo identidad + sesiones).
- **W5.5/W5.9/W5.10 — sesiones, dispositivos y magic links:** centro de **sesiones activas** + cierre **individual y global** (mantiene la actual, con verificación de pertenencia); **access token revocable** (validación de sesión en DB por request); centro de **dispositivos confiables** (trust/untrust/eliminar→revoca sesiones); **notificación de nuevo inicio de sesión** (notifier desacoplado + Mock); **historial de accesos** del cliente; **revocación automática al cambiar credenciales críticas** (hook para W5.8); **magic links de un solo uso** con expiración corta (emisión interna por secreto, consumo público, claim atómico).

## Commits
| Hash | Fecha | Descripción |
|---|---|---|
| `c5ea76b` | 26-jun | docs: ... + **plan WS-5 (gateway identidad OTP/JWT)** |
| `5b4bc1a` | 26-jun | feat(coc): WS-5 plan (sesiones cortas, sin API keys) + **W5.1 capa de datos gateway** |
| `4bf6c19` | 26-jun | feat(coc): **W5.6 handshake** — sesión Odoo efímera del usuario portal (sin API keys) |
| `f4be940` | 26-jun | feat(coc): **W5.2/W5.3** — OTP desacoplado (interfaz+Mock) + flujo + sesiones cortas |
| `0e739c1` | 26-jun | feat(coc): **W5.7** — flujo auth E2E Gateway↔Odoo validado en STAGING (datos reales) |
| `9f81ece` | 26-jun | feat(coc): **W5.5/W5.9/W5.10** — sesiones, dispositivos confiables y magic links |
| `e43934d` | 26-jun | feat(coc): **W5.8** — contraseñas Argon2, cambio, recuperación OTP, cambio de teléfono |
| `208fec7` | 26-jun | feat(coc): **integración EvoApi** como proveedor OTP real (resiliente, desacoplado) |

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
- **Suite automatizada Odoo:** 19/19 verde (incluye `test_coc_session`). Reinicio del Gateway: cubierto por diseño (el `odoo_session_id` vive en `portal_session`, gateway stateless).
- **W5.2/W5.3 — Suite automatizada del Gateway (SQLite + Mock OTP + Odoo Fake, SIN servicios externos): 12/12 verde.** Cubre: login end-to-end (access+refresh), OTP solo-hash, bloqueo tras 3 intentos, expiración, cooldown, rate-limit por teléfono, rotación de refresh + **detección de reuse** (revoca familia), logout, teléfono no-cliente (respuesta **neutra**), auditoría completa.
- **EvoApi — Suite Gateway: 36/36 verde** (driver: éxito, reintentos→éxito, todo-falla→False, circuit breaker abre y omite transporte, health ok/fail, sin OTP/api_key en logs). **Validación real en STAGING:** API EvoApi responde HTTP 200 y la credencial es válida; instancia WhatsApp `SentinelaWA` en estado **`close`** (requiere reconexión/QR antes del envío real). Health check del driver lo detecta correctamente.
- **W5.8 + W5.5/W5.9/W5.10 — Suite Gateway: 29/29 verde** (W5.8: política rechazada, set revoca otras sesiones, login por contraseña ok/mal, cambio con/sin/actual-incorrecto, recuperación por OTP, cambio de teléfono doble-verificación + revocación + el OTP resuelve el teléfono nuevo).
- **W5.5/W5.9/W5.10 — incluido arriba: 23 previos** (sesiones list/close/close-all, pertenencia, access revocable, dispositivos trust/untrust/remove, notificación de nuevo login, historial, revocación por cambio de credenciales, magic link emisión/consumo single-use/expirado/secreto).
- **W5.7 — E2E contra STAGING real (Mock OTP + `HttpOdooClient` real): 8/8 verde.** Perfiles validados con datos reales: cliente **nuevo** (creación lazy del usuario portal), **existente**, **empresarial** (25742), **multi-servicio** (25619), **suspendido** (25216, login OK), **usuario portal preexistente** (25757). Más: **concurrencia** de creación lazy (5 opens → sin duplicados), **refresh single-use + reuse** (revoca familia), **logout durante sesiones activas** (cierra la suya, las demás siguen). En cada login la **sesión Odoo real** devuelve el partner correcto en `/v1/me` (record rules WS-2). Datos de prueba creados y limpiados (rollback de teléfonos + borrado de temporales).

## Bugs
- Ninguno en la lógica. (Nota: un falso-fallo inicial del Bloque 3 fue **timing del harness** —odoo-lab aún cargaba tras el restart—; resuelto con espera robusta `--retry-all-errors`.)

## Rollback
- Gateway stateless en Docker: rollback = imagen anterior.
- DB del Gateway: respaldo antes de migraciones; migraciones reversibles.
- Endpoint interno en `sentinela_api`: aditivo; revertir commit + `-u` STAGING.
- No toca datos de negocio de Odoo.

## Estado
🚧 **En curso.** Hecho: W5.1 · **W5.6** · **W5.2/W5.3** · **W5.7 E2E (8/8)** · **W5.5/W5.9/W5.10** · **W5.8 contraseñas/recuperación/cambio de teléfono (29/29)**. **El sistema de identidad está COMPLETO** (OTP, contraseñas Argon2, sesiones cortas, dispositivos, magic links, recuperación, cambio de teléfono) y **EvoApi integrado** como proveedor real resiliente (36/36). **Pendiente para cerrar WS-5 al 100%:** reconectar la instancia WhatsApp `SentinelaWA` (QR) + smoke de **envío real** de OTP a un número de prueba. Después: **Sprint de Cierre** (consolidar WS-2 + WS-5 + EvoApi + smoke + pentest + rendimiento + release notes + runbook + rollback) → ventana única de despliegue a Producción.

# Release Notes — Portal COC · RC1 (WS-2 + WS-5 + EvoApi)

**Versión:** RC1 · **Fecha:** 2026-06-26 · **Componentes:** `sentinela_api 18.0.0.1.0` (Odoo addon) · `coc-gateway 0.2.0` (FastAPI).

## Resumen
Primera versión candidata del **Centro de Operaciones del Cliente (COC)**: capa de seguridad e identidad sobre Odoo 18. Habilita que clientes externos se autentiquen y que la API exponga datos **aislados por cliente**, sin duplicar lógica de negocio. **No incluye aún recursos de negocio** (Sprint 1 del portal) ni la SPA: es la base segura.

## Novedades

### WS-2 — Aislamiento de datos por cliente (Odoo)
- Grupo `group_coc_portal` + **usuario portal lazy** (se crea en el primer login).
- **Record rules** de aislamiento (`partner_id child_of commercial_partner`) en: suscripción, evento de alarma, dispositivo de monitoreo, orden FSM, documento de firma, factura (`out_*`).
- **ACL read-only** del grupo portal.
- Cierra además un **hueco pre-existente** de `digital_sign` (portal veía todos los documentos de firma).

### WS-5 — Identidad y sesiones (Gateway)
- **OTP** (proveedor desacoplado) con hash-only, TTL 5 min, 3 intentos, cooldown, rate-limit (IP/teléfono/dispositivo).
- **Sesiones cortas:** access JWT corto **revocable** + refresh **rotativo de un solo uso** con detección de reuse (revoca familia).
- **Handshake** con Odoo vía **sesión efímera** del usuario portal (sin credenciales permanentes) → las record rules de WS-2 son la primera línea de defensa.
- **Centro de sesiones** (listar, cerrar individual/global), **dispositivos confiables**, **historial de accesos**, **notificación de nuevo inicio de sesión**.
- **Contraseñas Argon2** + política, cambio, **login por contraseña**, **recuperación por OTP**.
- **Cambio seguro de teléfono** con doble verificación.
- **Magic links de un solo uso** (firma/autorizaciones) con expiración corta.
- **Revocación automática de todas las sesiones** al cambiar credenciales críticas.
- Biometría: responsabilidad del dispositivo/navegador (el Gateway solo identidad+sesiones).

### Integración EvoApi (proveedor OTP real)
- Driver intercambiable por config con **health check, circuit breaker, reintentos, manejo seguro de errores, métricas** (disponibilidad/latencia) y **sin loguear OTP/secretos**.

## Compatibilidad / impacto
- `sentinela_api` es un addon **nuevo y aditivo**: no modifica datos ni el comportamiento de usuarios internos (verificado: admin sigue viendo todo).
- Gateway y SPA son apps **standalone** (Docker), independientes del ciclo de Odoo.

## Limitaciones conocidas (RC1)
- Recursos de negocio del portal y SPA: fuera de alcance (siguientes sprints).
- Pagos en línea: Fase posterior.
- Instancia WhatsApp `SentinelaWA` debe estar **conectada** para envío real de OTP (fallback: contraseña).

## Validación
- Suite Gateway **36/36**; E2E con datos reales **8/8** (STAGING); PenTest **6/6**; aislamiento por cliente confirmado en los 6 modelos; rendimiento dentro de objetivo (ver `PERFORMANCE_COC.md`).

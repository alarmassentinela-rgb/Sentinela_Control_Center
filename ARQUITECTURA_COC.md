# Arquitectura final — Portal COC (RC1)

## 1. Vista de componentes
```
┌──────────────────────────────────────────────────────────────────────┐
│ CLIENTES                                                               │
│   SPA Web (Next.js, futura)        App móvil (futura)                  │
│        │  HTTPS · JWT (access corto)  ·  misma API                     │
└────────┼──────────────────────────────────────────────────────────────┘
         ▼   api.sentinela.mx  (Cloudflare + NPM)
┌──────────────────────────────────────────────────────────────────────┐
│ API GATEWAY / BFF  (FastAPI · Docker · stateless)                      │
│  Identidad: OTP (proveedor desacoplado) · contraseña Argon2 · biometría│
│  Sesiones cortas: access JWT REVOCABLE + refresh rotativo (reuse→revoca)│
│  Dispositivos confiables · magic links 1-uso · auditoría · rate-limit  │
│  Observabilidad: /health /metrics /v1/providers/health                 │
│  DB propia (Postgres): portal_identity, portal_session, refresh_token, │
│      otp_challenge, auth_audit_event, magic_link_token, trusted_device │
└───────┬───────────────────────────────────────────┬───────────────────┘
        │ LAN · secreto compartido + allowlist       │ driver OTP (config)
        ▼ (handshake: sesión Odoo efímera)           ▼
┌─────────────────────────────────┐        ┌──────────────────────────────┐
│ ODOO 18  ·  addon sentinela_api │        │ EvoApi (WhatsApp)            │
│  REST /v1/* (serializadores DTO)│        │ instancia SentinelaWA         │
│  /coc/internal/* (solo LAN)     │        │ health · circuit breaker      │
│  RECORD RULES de partner (WS-2) │        └──────────────────────────────┘
│  = 1ª línea de aislamiento      │
└───────┬─────────────────────────┘
        ▼  ORM (sin duplicar lógica)
┌──────────────────────────────────────────────────────────────────────┐
│ ODOO 18 — FUENTE DE VERDAD: sentinela_subscriptions / monitoring /     │
│   fsm / cfdi_prodigia / digital_sign  + integraciones (MikroTik,       │
│   Traccar, floLIVE, Prodigia)                                          │
└──────────────────────────────────────────────────────────────────────┘
```

## 2. Flujo de login (OTP) y aislamiento
```
SPA → Gateway /v1/auth/otp/request (phone)
      Gateway → proveedor OTP (EvoApi) envía código (hash en DB, TTL 5m, rate-limit)
SPA → Gateway /v1/auth/otp/verify (phone, code)
      Gateway consume OTP → resuelve phone→partner (Odoo internal, secreto)
      Gateway → Odoo: abre SESIÓN EFÍMERA del usuario portal lazy (no API key)
      Gateway emite access JWT (corto, revocable) + refresh (rotativo)
SPA → Gateway /v1/...  (Bearer access)
      Gateway → Odoo COMO el usuario portal (sesión efímera)
      Odoo aplica RECORD RULES → devuelve SOLO datos del partner
```
**Principio:** el Gateway decide *quién eres* (identidad); Odoo decide *qué ves* (autorización). Un bug en el gateway no puede exponer datos de otro cliente.

## 3. Flujo de magic link (firma / autorización)
```
Odoo → Gateway /coc/internal/magic/issue (secreto)  → token 1-uso, TTL corto
(cliente recibe enlace) → SPA → Gateway /v1/magic/consume (token)
      Gateway valida (no usado, no expirado) → marca usado (claim atómico) → contexto
```

## 4. Decisiones clave (ver ADRs en `docs/adr/`)
- Híbrida API-first + Gateway (ADR-0001); Odoo única fuente de verdad (ADR-0002).
- Record rules = 1ª línea (ADR-0003); usuario portal lazy + sesión efímera (ADR-0004).
- Sesiones cortas + refresh rotativo (ADR-0005); proveedores desacoplados (ADR-0006).
- Magic links 1-uso (ADR-0007); Argon2 + biometría en dispositivo (ADR-0008).
- Single-tenant con costuras (ADR-0009); STAGING-first + validación dinámica (ADR-0010); LAN allowlist (ADR-0011).

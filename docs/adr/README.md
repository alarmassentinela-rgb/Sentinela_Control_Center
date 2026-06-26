# Architecture Decision Records (ADR) — Portal COC

Registro de las principales decisiones de diseño. Formato: Contexto · Decisión · Consecuencias · Estado.

| ADR | Título | Estado |
|---|---|---|
| [0001](ADR-0001-arquitectura-hibrida-api-first-gateway.md) | Arquitectura híbrida API-first con Gateway (BFF) | Aceptada |
| [0002](ADR-0002-odoo-fuente-de-verdad.md) | Odoo como única fuente de verdad; no duplicar lógica | Aceptada |
| [0003](ADR-0003-record-rules-primera-linea.md) | Record rules de partner como 1ª línea de defensa | Aceptada |
| [0004](ADR-0004-usuario-portal-lazy-sesion-efimera.md) | Usuario portal lazy + sesión Odoo efímera (sin API keys) | Aceptada |
| [0005](ADR-0005-sesiones-cortas-refresh-rotativo.md) | Sesiones cortas: access revocable + refresh rotativo (reuse) | Aceptada |
| [0006](ADR-0006-proveedores-desacoplados-mock-first.md) | Proveedores desacoplados + Mock-first; EvoApi 1ª impl real | Aceptada |
| [0007](ADR-0007-magic-links-un-solo-uso.md) | Magic links de un solo uso solo para firma/autorización | Aceptada |
| [0008](ADR-0008-argon2-biometria-dispositivo.md) | Contraseñas Argon2; biometría del lado del dispositivo | Aceptada |
| [0009](ADR-0009-single-tenant-con-costuras.md) | Single-tenant ahora con costuras multiempresa | Aceptada |
| [0010](ADR-0010-staging-first-validacion-dinamica.md) | STAGING-first + validación dinámica con datos reales | Aceptada |
| [0011](ADR-0011-endpoints-internos-lan-secreto.md) | Endpoints internos: secreto compartido + allowlist LAN | Aceptada |

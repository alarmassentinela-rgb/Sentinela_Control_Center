# ADR-0011 — Endpoints internos: secreto compartido + allowlist LAN

**Estado:** Aceptada (26-jun-2026)

## Contexto
El handshake gateway↔Odoo (resolver teléfono, abrir/cerrar sesión efímera, set_phone, emitir magic links) usa endpoints `/coc/internal/*`. No deben ser accesibles desde internet ni por terceros.

## Decisión
Defensa en profundidad: (1) **secreto compartido** (header, comparación timing-safe, fail-closed); (2) **allowlist de CIDRs** (`coc_internal_allowed_cidrs`) que en Producción se fija a la red/IP del gateway; (3) a nivel de red, **no proxyear** `/coc/internal/*` por NPM/Cloudflare (solo LAN). Robustez: entradas malformadas → respuesta controlada (no 500).

## Consecuencias
- (+) Tres capas independientes; un fallo de una no compromete el resto.
- (+) Validado en STAGING (enforcement + allow + secreto inválido + sid malformado).
- (−) El allowlist requiere configurar el CIDR correcto en prod (documentado en runbook).

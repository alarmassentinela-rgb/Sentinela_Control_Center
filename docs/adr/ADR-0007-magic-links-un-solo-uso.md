# ADR-0007 — Magic links de un solo uso solo para firma/autorización

**Estado:** Aceptada (25/26-jun-2026)

## Contexto
Los enlaces sin login son cómodos pero riesgosos si se usan para acceso recurrente.

## Decisión
Los **magic links** se limitan a **firma de documentos y autorizaciones**; son de **un solo uso** (claim atómico) con **expiración corta**. El **login recurrente** usa OTP o contraseña (no magic links).

## Consecuencias
- (+) Superficie de riesgo acotada; reuso imposible.
- (+) Compatible con el patrón `portal.mixin`/token ya existente en Odoo.
- (−) El cliente debe re-solicitar si el enlace expira/ya se usó (intencional).

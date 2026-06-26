# ADR-0001 — Arquitectura híbrida API-first con Gateway (BFF)

**Estado:** Aceptada (25-jun-2026)

## Contexto
El Portal debe ser canal principal, escalar a miles, servir de base para app móvil y evolucionar independiente de Odoo, sin reescribir lo que ya funciona.

## Decisión
3 capas + gateway: **SPA/móvil → API Gateway/BFF (FastAPI) → addon `sentinela_api` (REST) → Odoo**. El gateway concentra la *experiencia* (identidad, OTP, agregación, caché, observabilidad) y evoluciona en su propio ciclo; el addon expone la *lógica de negocio* de Odoo.

## Consecuencias
- (+) UX desacoplada del ERP; misma API para web y móvil; iteración rápida en el gateway.
- (+) Odoo protegido detrás del gateway (no recibe tráfico público directo).
- (−) Una pieza más que operar (gateway). Mitigado: stateless + Docker + observabilidad.

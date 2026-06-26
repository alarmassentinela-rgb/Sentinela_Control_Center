# ADR-0009 — Single-tenant ahora con costuras para multiempresa

**Estado:** Aceptada (25-jun-2026)

## Contexto
Visión a futuro: plataforma multiempresa/white-label/SaaS. Pero la v1 debe enfocarse en Sentinela sin complejidad innecesaria.

## Decisión
Construir **single-tenant** (Sentinela) con **costuras** que permitan evolucionar sin rehacer: parámetros de negocio por config, branding vía `/v1/config/theme`, integraciones tras interfaz (drivers), backend Odoo leído de config, identidad lista para un campo `tenant` aditivo, capacidades por flags. Modelo objetivo futuro: **DB por inquilino** (ya se opera multi-DB con dbfilter).

## Consecuencias
- (+) Sin sobrecosto hoy; futuro multiempresa preservado.
- (+) Cada hardcode se "promueve" a config (alinea limpieza de deuda con producto).
- (−) Disciplina para no hardcodear; control plane se construye después.

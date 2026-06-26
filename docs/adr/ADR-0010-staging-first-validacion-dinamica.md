# ADR-0010 — STAGING-first + validación dinámica con datos reales

**Estado:** Aceptada (26-jun-2026)

## Contexto
El server no es git working tree; producción es sensible. Las pruebas sintéticas no siempre reflejan el comportamiento real.

## Decisión
- **STAGING-first:** todo se despliega y valida en `Sentinela_STAGING` antes de Producción; ventana única para prod.
- **Validación dinámica con datos reales** (no solo estática): correr suites + e2e + pentest + perf contra el sistema vivo en STAGING.

## Consecuencias
- (+) Detectó fugas/bugs que lo sintético no veía (hueco `sign.document`, sid malformado, concurrencia de refresh).
- (+) Confianza alta antes del Go-Live.
- (−) Requiere datos de prueba y limpieza; se automatizó (setup + rollback).

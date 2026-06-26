# ADR-0002 — Odoo como única fuente de verdad; no duplicar lógica

**Estado:** Aceptada (25-jun-2026)

## Contexto
Odoo 18 ya contiene clientes, servicios, facturación, tickets. Duplicar datos/lógica generaría inconsistencias y doble mantenimiento.

## Decisión
El Portal **no persiste datos de negocio** ni reimplementa reglas: `sentinela_api` **invoca métodos de modelo existentes** y serializa (DTOs). La auditoría reveló que la lógica ya vive en métodos de modelo (≈70-75% reutilizable).

## Consecuencias
- (+) Sin duplicación; una sola verdad; menos bugs de sincronización.
- (+) El trabajo es "exponer", no "reescribir".
- (−) El contrato de API depende de métodos de Odoo → se mitiga con serializadores DTO estables (un cambio de modelo no rompe al cliente).

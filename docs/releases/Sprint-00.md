# Sprint-00 — Análisis, Arquitectura y Diseño

**Fechas:** 2026-06-25 · **Estado:** ✅ Completado y aprobado

## Objetivo
Definir el producto y la arquitectura del Centro de Operaciones del Cliente (COC) antes de escribir código: entender el ERP existente, decidir la arquitectura, congelar el alcance v1 y diseñar la experiencia completa (residencial y empresarial).

## Cambios
- **PRD maestro** del COC con alcance v1 **congelado** (módulos, prioridades MoSCoW, roadmap por fases, costuras multiempresa documentadas, backlog).
- **Auditorías** de los módulos existentes (reutilización ~70–75%, dependencias, deuda técnica, escalabilidad) → estrategia "reutilizar, no duplicar".
- **Wireframes** en Markdown/ASCII de los flujos **residencial** (29 pantallas) y **empresarial** (multi-sucursal/usuario/servicio), con verificación de la regla de 3 interacciones.
- **Documento técnico de implementación** (puente diseño→dev): cada pantalla → módulos Odoo, modelos, APIs, seguridad, dependencias, fase.
- Decisiones de arquitectura: **API-first híbrida** (SPA → Gateway FastAPI → addon `sentinela_api` → Odoo); identidad en gateway; single-tenant con costuras para multiempresa.

## Commits
| Hash | Fecha | Descripción |
|---|---|---|
| `dcd0572` | 25-jun | docs: PRD maestro Portal COC v1 (alcance congelado) |
| `71bbda8` | 25-jun | docs: wireframes flujo residencial COC (aprobado v1) |
| `768620a` | 25-jun | docs: wireframes flujo empresarial COC (aprobado v1) |
| `77c8d2a` | 25-jun | docs: documento técnico de implementación COC (puente diseño-dev) |

## Riesgos
- Deuda técnica del ERP (god-object `subscription.py`, 0 tests, `except: pass`, **sin record rules**) → mitigación: pagar el bloqueador de seguridad antes del portal; el resto en paralelo.
- 43% de subs sin teléfono → impacta login OTP (campaña de captura en paralelo).

## Pruebas
- N/A (fase de diseño). Validación = revisión y aprobación de Enrique por entregable.

## Bugs
- Ninguno (sin código). Se **identificó** el bloqueador: ausencia de record rules de aislamiento por cliente.

## Rollback
- N/A (documentos versionados en git; reversibles por commit).

## Estado
✅ **Completado.** Diseño funcional y técnico aprobado y congelado. Habilita Sprint-01 (cimientos).

# Política de Evolución del Portal de Clientes (incremental)

**Fecha:** 28-jun-2026 · Alea Platform · **Reemplaza el orden "Gateway primero":** el Portal mantiene su roadmap; la arquitectura de plataforma se adopta **incrementalmente, sin rehacer trabajo**.

## Objetivo
Terminar el Portal de Clientes **con el roadmap actual** y, a la vez, prepararlo para **evolucionar naturalmente** hacia la arquitectura completa de Alea Platform **sin rehacer lo ya construido**.

## Reglas operativas (obligatorias durante el desarrollo del Portal)
1. **No romper el Portal.** Nada de refactorizaciones grandes solo por motivos arquitectónicos. La evolución es **incremental**; lo que ya funciona se respeta.
2. **Integración progresiva.** Cada **nueva** funcionalidad del Portal consume, **cuando exista**, la **Catalog Public Interface v1** del Catalog Engine. **Prohibido** agregar **nuevas** llamadas directas a Syscom (lo existente se migra cuando toque, sin urgencia de refactor).
3. **Gateway como evolución, no requisito.** El **Alea API Gateway** queda en el **roadmap** de Alea Platform; **NO es requisito para terminar el Portal**. Se introducirá **cuando aporte valor**, como capa de agregación entre el Portal y los motores (el diseño ya está en `BLUEPRINT_ALEA_API_GATEWAY_28JUN2026.md`).
4. **Mantener contratos.** Toda integración nueva se hace por **contratos públicos** (Catalog v1, ERP API). **Prohibido** el acoplamiento directo del Portal con módulos internos (ORM de Odoo, API de Syscom).
5. **Revisión de arquitectura antes de cada feature.** Antes de cada nueva funcionalidad: revisar si **ya existe un servicio reutilizable** en Alea Platform. **Reutilizar antes de crear** lógica nueva (regla de las 3 preguntas del Master Plan).

## Estado actual vs. objetivo (transición incremental)
- **Hoy:** el Portal (SPA + su BFF) consume datos del ERP vía `sentinela_api`; el catálogo aún puede no estar conectado al Catalog Engine.
- **Paso a paso:** las **nuevas** features de catálogo del Portal apuntan a **Catalog Public Interface v1**; lo viejo se migra cuando se toque (sin big-bang).
- **Objetivo (cuando aporte valor):** introducir el **Alea API Gateway** como front único; el Portal y la App consumen el Gateway. Hasta entonces, el Portal puede llamar a los contratos públicos (Catalog v1 / ERP API) directamente.

## Qué NO haremos
- No detener ni rediseñar el Portal por arquitectura.
- No big-bang del Gateway.
- No nuevas llamadas directas a Syscom ni al ORM desde el Portal.

> En resumen: **prioridad Portal + evolución incremental + contratos públicos + reutilizar antes de crear.** El Gateway llega cuando su valor lo justifique, sin frenar el Portal.

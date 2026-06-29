# S2-000 — Preparación del Sprint 2 (Cobranza) · Checklist

> Historia **S2-000** del backlog oficial (`SPRINT_02_COBRANZA_BACKLOG.md`). **Sin tocar código de negocio.**
> Cierra solo cuando todos sus criterios de aceptación están en verde. Gate del Sprint 1: **"La UAT terminó."** ✅ (emitido 29-jun-2026).

## Criterios de aceptación

- [x] **Rama de Sprint 2 creada, separada de la línea base del Sprint 1.**
  - Rama: `sprint2-cobranza` (creada desde `main` = Sprint 1 liberado / RC `coc-v1.1.0-rc1`).
  - `main` queda como la **referencia oficial de Producción**; el desarrollo del Sprint 2 ocurre en la rama.

- [x] **Entorno de desarrollo levanta.**
  - Gateway: suite de pruebas **56 passed, 8 skipped** (sin fallos). Deps core verificadas (fastapi, sqlalchemy, httpx, pydantic, pytest 9.1.1).
  - SPA: `tsc --noEmit` (typecheck) **OK**; dependencias node instaladas.

- [x] **Dependencias instaladas/confirmadas.**
  - Gateway: `sentinela_coc/gateway/requirements.txt` presente; entorno con deps resueltas.
  - SPA: `sentinela_coc/web` con `node_modules` y build verificado en el Sprint 1.

- [x] **Variables de entorno confirmadas (incluida config de Stripe en modo test).**
  - Añadidos **placeholders de Stripe (MODO TEST)** en `.env.example` (config, **no** código de negocio):
    - Gateway (`sentinela_coc/.env.example`): `COC_STRIPE_SECRET_KEY` (sk_test_), `COC_STRIPE_WEBHOOK_SECRET` (whsec_), `COC_STRIPE_PUBLISHABLE_KEY` (pk_test_).
    - SPA (`sentinela_coc/web/.env.example`): `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` (pk_test_).
  - Las claves reales viven **solo en `.env`** (no se commitean). Las cuentas/llaves de prueba de Stripe se cargarán al llegar a **S2-006**.

- [x] **STAGING del Sprint 1 intacto + desarrollo en entorno separado.**
  - Contenedores STAGING Sprint 1 **arriba e inalterados**: `coc-gw-staging`, `coc-web-staging`.
  - **Producción intacta**: gateway `0.3.2` (`https://api.sentinela.mx/health`), SPA `https://portal.sentinela.mx/login` → 200.
  - **Regla:** el desarrollo del Sprint 2 NO reutiliza los contenedores congelados del Sprint 1. Cuando una historia requiera ejecución (a partir de S2-001), se levantará un **entorno separado** (p. ej. contenedores/puertos dedicados de Sprint 2), sin tocar STAGING/PROD del Sprint 1.

- [x] **Cero cambios a código de negocio.**
  - Solo se modificaron `.env.example` (gateway + SPA) y se añadió este checklist. Ningún `*.py`/`*.tsx`/modelo/ruta/manifest de negocio fue tocado.

## Contrato de construcción (recordatorio para las siguientes historias)
- Ciclo por historia: **Desarrollo → Pruebas → Validación → Commit → Revisión → siguiente.**
- No trabajar dos historias con dependencia mutua en paralelo.
- No ampliar alcance, no modificar el spec; cambios de arquitectura solo ante necesidad real durante la implementación (vía RFC).
- Orden del backlog: **S2-000** → S2-001 (Event Store) ∥ S2-003 (Ledger adapter) → … → S2-015 (aceptación).

## Estado
✅ **S2-000 COMPLETADA.** Entorno listo. Próxima historia: **S2-001 — Event Store mínimo** (`append/read/byAggregate`).

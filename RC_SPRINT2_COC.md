# Release Candidate — Sprint 2 (Vertical COBRANZA)

**RC oficial:** `coc-v1.2.0-rc1` · **Rama:** `release/sprint2-cobranza` (limpia, solo Cobranza) · **Base:** `main` (= Sprint 1 en Producción) · **Fecha:** 2026-06-30.
**Estado:** EN ESPERA DE APROBACIÓN (Etapa 1 del `PLAN_RC1_SPRINT2_COBRANZA.md`). **No desplegado.**

> Alcance **1:1 con el Sprint 2 Cobranza** (decisión aprobada): la rama de desarrollo `sprint2-cobranza` contenía también cambios de `sentinela_subscriptions` (cobro adelantado global) que **NO** forman parte de este RC. Se aislaron creando esta rama limpia desde `main` y **cherry-pick** (`-x`) de los 18 commits de la vertical Cobranza; los 8 commits ajenos (Suscripciones/skill) quedaron fuera.

## 1. Correspondencia 1:1
Spec (`SPRINT_02_COBRANZA.md`) ↔ Acta (`CIERRE_TECNICO_SPRINT2_COBRANZA.md`) ↔ **este RC** ↔ UAT (Etapa 4) ↔ Release (Etapa 7). El RC contiene **solo** la vertical Cobranza.

## 2. Versiones del RC
| Componente | Prod hoy (anterior) | RC Sprint 2 |
|---|---|---|
| Gateway (BFF) | 0.3.2 | **0.4.0** |
| SPA | (Sprint 1) | **0.5.0** |
| sentinela_api | 18.0.0.2.0 | **18.0.0.3.0** |
| Umbrella (tag) | `coc-v1.1.0-rc1` | **`coc-v1.2.0-rc1`** → (final) `coc-v1.2.0` |

## 3. Commits del RC (rama limpia `release/sprint2-cobranza`)
18 commits de Cobranza (cherry-picked desde la rama de desarrollo; cada uno traza al original vía `-x`):

| # | Historia | Commit (RC) |
|---|---|---|
| S2-000 | Preparación del Sprint | `556a82e` |
| S2-001 | Event Store mínimo | `f5e0764` |
| S2-002 | Catálogo de eventos | `47e7378` |
| S2-003 | Ledger: adaptador (lectura) | `7a69481` |
| S2-004 | Ledger: Estado de Cuenta | `6c61810` |
| S2-005 | Puerto PaymentAdapter + Motor | `668b22b` |
| S2-006 | Adaptador Stripe | `5c07e9a` |
| S2-007 | Intención + startPayment | `6069a17` |
| S2-008 | Webhook (idempotente) | `0ae0a3c` |
| S2-009 | Aplicación de pago + factura.pagada | `6782642` |
| S2-010 | CFDI async reintetable | `d69ec06` |
| S2-011 | Reactivation Policy | `971f195` |
| S2-012 | Notificación | `cba0512` |
| S2-013 | Indicadores MVP | `e224c7c` |
| S2-014 | SPA: pago en línea | `a07c741` |
| S2-015 | Aceptación E2E + cascada | `fee331b` |
| docs | Cierre técnico | `1816d5d` |
| docs | Plan RC1 | `9eb1b36` |

*(+ commit de bumps de versión + este manifiesto, sobre el que apunta el tag.)*
**Excluidos (NO en el RC):** 8 commits de `sentinela_subscriptions` (D1/D2/D3 cobro adelantado global + fixes) y skill `deploy-modulo` + guía UAT de Suscripciones.

## 4. Aislamiento verificado (solo Cobranza)
- `git diff main..HEAD -- sentinela_subscriptions` → **vacío**.
- `git diff main..HEAD -- .claude` → **vacío**.
- Módulos tocados: **solo** `sentinela_coc/` (gateway + web), `sentinela_api/` (controllers) y 4 docs de Cobranza.

## 5. Paridad funcional (código validado == RC)
La rama limpia se ejecutó en el entorno de integración (contenedor desechable):
- Gateway suite unitaria: **148 passed / 8 skipped**.
- Aceptación E2E §12: **7/7 PASS** (`tests/e2e_sprint2_cobranza.py`).
- Sintaxis de los 5 controllers Odoo nuevos: OK.
- Diffs idénticos a la rama de desarrollo aprobada (cherry-pick), sin cambios de Suscripciones → **la funcionalidad aprobada del Sprint 2 está íntegra**.

## 6. Artefactos a desplegar (se construyen desde el tag)
| Artefacto | Construcción | Identidad |
|---|---|---|
| Gateway 0.4.0 | `docker compose up --build` desde el RC | digest al construir (acta de despliegue) |
| SPA 0.5.0 | `docker build` con `NEXT_PUBLIC_API_BASE` + `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | digest al construir |
| sentinela_api 18.0.0.3.0 | rsync + `-u` (módulo Odoo) | versión del módulo |
> Reproducibilidad por **fuente** (tag `coc-v1.2.0-rc1`). Digests se registran al construir en STAGING (Etapa 3) y en PROD (Etapa 7).

## 7. Rollback → versiones inmediatamente anteriores
| Componente | RC (nueva) | Rollback (anterior, en Prod) |
|---|---|---|
| Gateway | 0.4.0 | **0.3.2** (imagen prod vigente; re-tag antes de la ventana) |
| SPA | 0.5.0 | Sprint 1 (contenedor prod actual) |
| sentinela_api | 18.0.0.3.0 | **18.0.0.2.0** (desinstalar/`-u` al commit previo; aditivo) |
| Umbrella | `coc-v1.2.0` | **`coc-v1.1.0-rc1`** |
- DB del gateway y DB Odoo se respaldan antes de cada ventana (STAGING y PROD).

## 8. Veredicto
✅ **RC `coc-v1.2.0-rc1` armado, aislado (solo Cobranza) y con paridad funcional verificada.** Listo para tu **aprobación de la Etapa 1**. Tras aprobarla: Etapa 2 (validación técnica del RC) → Etapa 3 (STAGING con Odoo + Stripe test). **Nada se despliega sin tu autorización.**

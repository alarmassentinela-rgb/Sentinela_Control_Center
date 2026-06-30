# Evidencia — Sprint 2 (Vertical COBRANZA) · Portal COC

**Fecha cierre:** 2026-06-30 · **Rama:** `sprint2-cobranza` · **Spec:** `SPRINT_02_COBRANZA.md` + backlog `SPRINT_02_COBRANZA_BACKLOG.md`.
**Resultado:** ✅ **16 historias (S2-000…S2-015) construidas, probadas y aprobadas una por una.** Aceptación §12 verde.

> Disciplina: cada historia siguió **Desarrollo → Pruebas → Validación → Commit → Revisión** antes de la siguiente. Capacidades nacidas **mínimas**, exigidas por Cobranza (filosofía de la plataforma). Todo el desarrollo en un **entorno de integración separado** (contenedor desechable de gateway), sin tocar STAGING/PROD del Sprint 1 (congelado).

## 1. Historias y commits
| # | Historia | Commit |
|---|---|---|
| S2-000 | Preparación del Sprint (sin código de negocio) | `0f9ee6e` |
| S2-001 | Event Store mínimo (append/read/byAggregate) | `5bd3b54` |
| S2-002 | Catálogo de eventos de Cobranza | `249035d` |
| S2-003 | Ledger: adaptador contable (lectura) | `85e81d0` |
| S2-004 | Ledger: Estado de Cuenta | `6caae4e` |
| S2-005 | Puerto PaymentAdapter + Motor de Pago | `3c527c5` |
| S2-006 | Adaptador Stripe (primer PaymentAdapter) | `6b557b6` |
| S2-007 | Intención de pago + endpoint startPayment | `45bb5bb` |
| S2-008 | Webhook → pago.confirmado/rechazado (idempotente) | `f69c998` |
| S2-009 | Aplicación de pago + factura.pagada | `83f3875` |
| S2-010 | CFDI async reintetable | `65b9900` |
| S2-011 | Reactivation Policy (por servicio) | `e762649` |
| S2-012 | Notificación de confirmación | `6669ddf` |
| S2-013 | Indicadores MVP (cobrado hoy/cartera/pendientes) | `fb0f8cc` |
| S2-014 | SPA: startPayment() + UX de confirmación | `77460e3` |
| S2-015 | Aceptación E2E + ensamblado (cascada) + evidencia | *(este commit)* |

## 2. Capacidades nacidas (mínimas) en el gateway
- **Eventos** (`capabilities/events`): Event Store (`coc_event`, idempotencia por `event_id`) + Catálogo de Cobranza (tipos + criticidad + esquema mínimo; `append` rechaza tipo desconocido). Agnóstico del dominio; eventos inmutables.
- **Ledger** (`capabilities/ledger`): `AccountingAdapter` (solo hechos), Estado de Cuenta (`saldo/vencido/por vencer`), `reconcile_payment` (validación de intención), Indicadores MVP. Única fuente del cálculo financiero; no duplica la contabilidad.
- **Pagos** (`capabilities/payments`): puerto `PaymentAdapter` + Motor (sin proveedor), adaptador **Stripe** (primer adaptador; SDK no se filtra), `startPayment` (valida contra el Ledger → publica `pago.iniciado`), **webhook** (firma + idempotente → `pago.confirmado/rechazado`), **aplicación de pago** (conciliación + `factura.pagada`).
- **CFDI** (`capabilities/cfdi`): consumidor async reintetable (un fallo del PAC nunca invalida el pago).
- **Reactivación** (`capabilities/reactivation`): Policy por servicio (3 condiciones → `servicio.reactivado`).
- **Notificaciones** (`capabilities/notifications`): confirmación reusando el canal existente; sin mensajería nueva.
- **Cobranza** (`capabilities/cobranza`): **cascada** que ensambla los consumidores (S2-015), disparada por el webhook (fail-safe).

## 3. Aceptación E2E (§12) — `tests/e2e_sprint2_cobranza.py`
Ensambla la cascada sobre el **Event Store real** + puertos Fake de los sistemas externos. **7/7 PASS:**
| Escenario §12 | Resultado |
|---|---|
| Camino feliz: pago→Ledger→factura.pagada→CFDI→Policy→notificación | ✅ |
| Idempotencia (se aplica/propaga una sola vez) | ✅ |
| Conciliación (no duplica con depósito ya pagado) | ✅ |
| CFDI: fallo del PAC → pendiente reintetable, **pago válido** | ✅ |
| Reactivación **por servicio** (solo el que cumple las 3 condiciones) | ✅ |
| Estado de Cuenta **desde el Ledger** | ✅ |
| Motor de Pago **sin Stripe directo** (AST de imports) | ✅ |

## 4. Pruebas (entorno de integración)
- **Gateway — suite unitaria: 148 passed / 8 skipped** (cada historia con sus pruebas).
- **Gateway — aceptación E2E: 7/7 PASS** (corrida explícita, igual patrón que el e2e del Sprint 1).
- **SPA (S2-014): 4/4 estados** (Playwright con intercepción de red) + typecheck + lint + build limpios.
- **Sin regresión** en ninguna historia a lo largo del sprint.

## 5. Cumplimiento de arquitectura (regla de oro)
- Capacidades **mínimas**; sin Timeline, Dashboard Engine, CQRS/Replay/Projections, medios guardados ni abstracciones adelantadas.
- **Puertos/adaptadores**: Ledger↔contable, Motor↔proveedor, CFDI↔PAC, Reactivación↔suscripciones, Notificación↔canal. El dominio nunca conoce Odoo/Stripe directamente.
- **Consumidores desacoplados** por eventos; **idempotencia** anclada en el Event Store; **fail-safe** (CFDI/notificación nunca rompen el pago).
- **SPA sin lógica de negocio** (solo presenta/comanda/muestra).

## 6. Pendiente de despliegue (NO ejecutado)
Los **endpoints internos de Odoo** (`/coc/internal/payments/apply`, `/cfdi/stamp`, `/reactivation/*`, `/notify/*`, `/v1/ledger/movements`) y la **integración viva con Stripe** (claves `sk_test_`/`whsec_` + Stripe.js) se validan en el **despliegue del Sprint 2 a STAGING**, que —como el Sprint 1— requiere **autorización explícita y ventana**. STAGING del Sprint 1 permanece congelado; nada se desplegó a producción durante el desarrollo del Sprint 2.

## 7. Veredicto
✅ **Sprint 2 (vertical Cobranza) COMPLETO en código y aceptación E2E.** Listo para el cierre del Sprint y, tras tu autorización, para planear el despliegue a STAGING (validación viva de Odoo/Stripe) y posteriormente a Producción.

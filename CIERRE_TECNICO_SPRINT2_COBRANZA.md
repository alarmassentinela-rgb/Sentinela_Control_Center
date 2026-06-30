# Cierre Técnico — Sprint 2 (Vertical COBRANZA) · Portal COC

**Fecha:** 2026-06-30 · **Rama:** `sprint2-cobranza` (desde `main` = Sprint 1 liberado) · **Spec:** `SPRINT_02_COBRANZA.md` + backlog `SPRINT_02_COBRANZA_BACKLOG.md`.
**Naturaleza:** Acta de cierre del **desarrollo**. La liberación (RC → STAGING Odoo/Stripe test → plan → Producción → reporte) es una etapa **independiente y posterior**.

---

## 1. Objetivo del Sprint
**El cliente paga sus facturas en línea y queda al corriente, sin fricción**, y lo refleja en su Estado de Cuenta — acelerando cobranza, bajando morosidad y eliminando conciliación manual. Primera **vertical de negocio** sobre la plataforma Alea, haciendo **nacer capacidades reales con el contrato mínimo** que esta vertical exige (filosofía: una capacidad se reutiliza solo cuando una 2ª vertical lo demuestra).

## 2. Alcance comprometido vs. entregado
| Comprometido (spec §1 IN) | Entregado |
|---|---|
| Pagar facturas (liquidación total) con tarjeta **vía Motor de Pago** | ✅ Motor + adaptador Stripe + `startPayment` (seam SPA cableada) |
| Confirmación (confirmado/en proceso/rechazado) | ✅ Webhook + UX SPA de 3 estados |
| **Ledger financiero mínimo** (fuente del Estado de Cuenta) | ✅ Adaptador + Estado de Cuenta + reconciliación |
| **factura.pagada** + aplicación de pago | ✅ Aplicación + conciliación + evento |
| **CFDI desacoplado** (async, reintetable) | ✅ Consumidor CFDI; fallo PAC no invalida el pago |
| **Reactivación por Policy** | ✅ Policy por servicio (3 condiciones) |
| **Event Store mínimo** | ✅ append/read/byAggregate + idempotencia |
| **Notificación** de confirmación (canal existente) | ✅ Consumidor reusando el mail de Odoo |
| **Indicadores MVP** (3 consultas) | ✅ cobrado hoy / cartera vencida / pagos pendientes |

**Fuera de alcance (spec §1 OUT) — NO construido (correctamente):** Timeline · pago recurrente / medio guardado · pago parcial / planes · reembolso/disputa self-service · Dashboard Engine · CQRS/Replay/Projections/Event Sourcing · más métodos/proveedores. **Sin desviaciones de alcance.**

> Matiz de entrega: el **seam** `startPayment()` + UX de 3 estados quedó cableado; la **captura de tarjeta con Stripe.js/Elements** (3DS, usando el `client_secret` que ya entrega el backend) es la capa siguiente del proceso de liberación. No es alcance nuevo: es la integración viva con el proveedor.

## 3. Historias S2-000…S2-015 — estado final
| # | Historia | Commit | Estado |
|---|---|---|---|
| S2-000 | Preparación del Sprint (sin código de negocio) | `0f9ee6e` | ✅ Aprobada |
| S2-001 | Event Store mínimo (append/read/byAggregate) | `5bd3b54` | ✅ Aprobada |
| S2-002 | Catálogo de eventos de Cobranza | `249035d` | ✅ Aprobada |
| S2-003 | Ledger: adaptador contable (lectura) | `85e81d0` | ✅ Aprobada |
| S2-004 | Ledger: Estado de Cuenta | `6caae4e` | ✅ Aprobada |
| S2-005 | Puerto PaymentAdapter + Motor de Pago | `3c527c5` | ✅ Aprobada |
| S2-006 | Adaptador Stripe (primer PaymentAdapter) | `6b557b6` | ✅ Aprobada |
| S2-007 | Intención de pago + endpoint startPayment | `45bb5bb` | ✅ Aprobada |
| S2-008 | Webhook → pago.confirmado/rechazado (idempotente) | `f69c998` | ✅ Aprobada |
| S2-009 | Aplicación de pago + factura.pagada | `83f3875` | ✅ Aprobada |
| S2-010 | CFDI async reintetable | `65b9900` | ✅ Aprobada |
| S2-011 | Reactivation Policy (por servicio) | `e762649` | ✅ Aprobada |
| S2-012 | Notificación de confirmación | `6669ddf` | ✅ Aprobada |
| S2-013 | Indicadores MVP | `fb0f8cc` | ✅ Aprobada |
| S2-014 | SPA: startPayment() + UX de confirmación | `77460e3` | ✅ Aprobada |
| S2-015 | Aceptación E2E + ensamblado (cascada) + evidencia | `f32529f` | ✅ Aprobada |

**16/16 historias aprobadas**, cada una con ciclo Desarrollo→Pruebas→Validación→Commit→Revisión.

## 4. Capacidades que NACIERON durante el Sprint (mínimas)
- **Eventos** (`capabilities/events`): Event Store (`coc_event`; idempotencia por `event_id`) + Catálogo de Cobranza (tipos + criticidad + esquema mínimo; rechaza tipo desconocido).
- **Ledger** (`capabilities/ledger`): `AccountingAdapter` (lectura de hechos) · Estado de Cuenta (saldo/vencido/por vencer) · `reconcile_payment` · Indicadores MVP.
- **Pagos** (`capabilities/payments`): puerto `PaymentAdapter` + Motor + adaptador Stripe + `startPayment` + webhook + aplicación de pago.
- **CFDI** (`capabilities/cfdi`): consumidor async reintetable (coordina; sin reglas fiscales).
- **Reactivación** (`capabilities/reactivation`): Policy por servicio.
- **Notificaciones** (`capabilities/notifications`): consumidor de confirmación.
- **Cobranza** (`capabilities/cobranza`): cascada que **ensambla** los consumidores.

## 5. Capacidades / activos REUTILIZADOS (no reinventados)
- **Identidad** del cliente y aislamiento por record rules (Sprint 1, WS-2).
- **Facturas / cuenta** (`sentinela_api`: account.move/payment) como fuente contable, vía adaptador.
- **Timbrado CFDI** (`sentinela_cfdi_prodigia.action_cfdi_stamp_prodigia`).
- **Canal de mail** de Odoo (notificación al cliente).
- **UX de selección + resumen + seam `startPayment`** y **Design System** del Sprint 1.
- **Gateway** (BFF) y su handshake de sesión efímera.

## 6. Principales decisiones de arquitectura
1. **Puertos/adaptadores en cada frontera** — Ledger↔contable, Motor↔proveedor, CFDI↔PAC, Reactivación↔suscripciones, Notificación↔canal. El dominio nunca conoce Odoo/Stripe directamente.
2. **Event Store como columna vertebral de integración** — los consumidores se desacoplan por eventos; la correlación pago↔factura usa el agregado `payment:<id>`.
3. **Idempotencia anclada en el Event Store** — `event_id` únicos/estables (webhook por id del proveedor; `factpagada:<pago>:<factura>`; `reactivado:<svc>:<inv>`).
4. **Consumidores fail-safe** — CFDI y notificación nunca rompen el pago (traducen fallos a estado reintetable / no bloquean).
5. **Cascada de orquestación** (S2-015) — el webhook dispara el ensamblado; corta en seco sin `pago.iniciado` (mantuvo S2-008 intacto).
6. **Validación financiera centralizada en el Ledger** — `reconcile_payment` valida la intención; la SPA no calcula.
7. **Import perezoso del SDK de Stripe** — el adaptador se inyecta; la suite corre sin el paquete.

## 7. Invariantes registrados durante las revisiones
**Event Store:** (1) agnóstico del dominio; (2) eventos inmutables (cambio = nuevo evento); (3) tipos de evento = contratos estables (no renombrar/reusar; semántica nueva = tipo nuevo).
**Ledger:** (1) AccountingAdapter = solo traductor de hechos (sin saldo/vencido/estado/indicadores); (2) toda la lógica del Estado de Cuenta vive en el Ledger; (3) `AccountStatement` = DTO de salida (sin lógica; ampliable retro-compatible).
**Pagos:** (1) Motor agnóstico del proveedor; (2) `idempotency_key` la provee el caso de uso (el Motor solo valida/propaga); (3) el adaptador nunca expone objetos/excepciones del SDK; (4) `startPayment` atómico de negocio; (5) webhook fail-safe (reintetable sin efectos duplicados); (6) aplicación de pago transaccional (sin aplicación confirmada no hay `factura.pagada`); (7) las notificaciones nunca bloquean el flujo.
**Reactivación:** la Policy es completamente determinista (misma entrada → misma decisión; sin depender del orden de consumidores, la hora ni efectos externos).
**CFDI:** el `CfdiConsumer` no contiene reglas fiscales (solo coordina/traduce; la lógica fiscal vive en el sistema fiscal).
**SPA:** nunca contiene lógica de negocio (solo presenta/comanda/muestra; toda regla financiera/validación en el backend).
**Indicadores:** alcance **exclusivo del cliente autenticado** (las vistas agregadas de cobranza son un backoffice futuro, fuera del Portal y del Sprint 2).

## 8. Riesgos conocidos diferidos deliberadamente a futuros Sprints
- **Timeline / consumo de eventos en UI** — nace cuando una 2ª vertical lo demuestre (regla de oro).
- **Dashboard Engine · CQRS/Replay/Projections/Event Sourcing** — no se adelantan.
- **Pago recurrente / medio guardado · pago parcial / planes · reembolso-disputa self-service · más métodos/proveedores** — fuera de alcance del MVP.
- **Vistas agregadas de cobranza (operador/backoffice)** — producto de administración futuro.
- **Stripe.js / Elements (captura de tarjeta + 3DS)** — capa de integración viva del proceso de liberación (el seam ya entrega `client_secret`).
- **Detalles del lado Odoo a confirmar EN VIVO (deploy):** vinculación factura↔suscripción y "otras vencidas por servicio" en reactivación; plantilla branded de la notificación; semántica de residual de notas de crédito.

## 9. Evidencia consolidada
- **Pruebas (entorno de integración — contenedor desechable `coc_s2_dev`):**
  - Gateway **suite unitaria: 148 passed / 8 skipped** (línea base Sprint 1 = 56 → **+92 pruebas del Sprint 2**).
  - Gateway **aceptación E2E §12: 7/7 PASS** (`tests/e2e_sprint2_cobranza.py`).
  - **SPA (S2-014): 4/4 estados** (Playwright con intercepción de red) + typecheck + lint + build limpios.
  - **Sin regresión** en ninguna historia a lo largo del sprint.
- **Cobertura funcional §12:** camino feliz · idempotencia · conciliación · CFDI reintetable (pago válido) · reactivación por servicio · Estado de Cuenta desde el Ledger · Motor sin Stripe directo.
- **Documentos generados:** `SPRINT_02_COBRANZA.md` (spec), `SPRINT_02_COBRANZA_BACKLOG.md`, `SPRINT_02_S2-000_CHECKLIST.md`, `EVIDENCIA_SPRINT2.md`, este `CIERRE_TECNICO_SPRINT2_COBRANZA.md`.
- **Memoria de invariantes:** `reference_event_store_invariants`, `reference_ledger_invariants`, `reference_payments_invariants`, `reference_cfdi_consumer_invariant`, `reference_reactivation_invariant`, `reference_spa_invariant`, `project_sprint2_cobranza`.

## 10. Lecciones aprendidas
- **Capacidades mínimas exigidas por la vertical** funcionó: cada pieza nació pequeña, con su contrato, y se mantuvo agnóstica — sin sobre-ingeniería.
- **Disciplina por historia** (una historia = un commit, pruebas antes de revisión) dio trazabilidad total y cero regresión; los **invariantes** capturados en cada revisión se volvieron guía viva.
- **Puertos + Fakes** permitieron probar toda la lógica de negocio **sin Odoo/Stripe vivos**, manteniendo STAGING/PROD del Sprint 1 congelados; el costo es que la integración viva con externos queda explícitamente para el deploy.
- **Consumidores desacoplados** evitaron acoplar el webhook a la contabilidad/CFDI; el **ensamblado tardío** (cascada) preservó historias previas intactas.
- **Entorno de integración separado** (contenedor desechable) fue clave para iterar sin tocar lo congelado.
- Pendiente de mejora: un **framework de pruebas del front** en el repo (hoy la SPA se valida con Playwright externo).

## 11. Declaración formal
✅ **DESARROLLO DEL SPRINT 2 — COBRANZA: CONCLUIDO.**
Las 16 historias S2-000…S2-015 están construidas, probadas y aprobadas. La aceptación §12 está verde. **Nada se desplegó** a STAGING ni a Producción durante el desarrollo.

Acordado el siguiente paso: tras la aprobación de esta acta, se **congela la rama `sprint2-cobranza`** y recién entonces inicia el **proceso de Release Candidate del Sprint 2**, con la misma disciplina del Sprint 1.

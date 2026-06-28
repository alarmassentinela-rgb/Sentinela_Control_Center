# Sprint 2 — Backlog ejecutable (vertical Cobranza)

> Descomposición construible de `SPRINT_02_COBRANZA.md` (contrato de construcción). Historias pequeñas,
> independientes y validables. **No se modifica el spec durante la implementación** salvo necesidad real
> aprobada. Mejoras detectadas → RFC/backlog, no se implementan. **No se inicia código hasta cerrar la
> UAT del Sprint 1.** Rutas de archivos = *probables* (gateway = `sentinela_coc/gateway`, SPA = `sentinela_coc/web`, Odoo = `sentinela_api`).

Convención de orden: las capacidades nacen primero (Event Store, Ledger, Pagos) y luego los consumidores.
Cada historia es testeable de forma aislada (con *fakes*/stubs donde dependa de otra).

## Regla de ciclo por historia (obligatoria)
Cada historia debe completar este ciclo **antes** de comenzar la siguiente:
**Desarrollo → Pruebas unitarias → Validación funcional → Commit → Revisión → (solo entonces) siguiente historia.**
**No se permite trabajar simultáneamente en dos historias que tengan dependencias entre sí.** (Solo
pueden solaparse historias sin dependencia mutua, p. ej. Event Store ∥ Ledger.)

---

### S2-000 — Preparación del Sprint
- **Objetivo:** dejar listo el arranque, **sin tocar código de negocio**: verificar entorno de desarrollo, confirmar dependencias, ramas y variables de entorno, confirmar que **STAGING permanece congelado** y que el desarrollo ocurre en un **entorno separado**.
- **Dependencias:** ninguna.
- **Criterios de aceptación:** entorno de desarrollo levanta; dependencias instaladas; rama de Sprint 2 creada (separada de la del Sprint 1); variables de entorno confirmadas (incluida la config de Stripe en modo test); STAGING del Sprint 1 intacto; checklist registrado. **Cero cambios a código de negocio.**
- **Archivos probables:** ninguno de negocio (solo rama/config/checklist; posible `.env.example` o nota de entorno).
- **Complejidad:** S.
- **Commit:** `chore(sprint2): preparación y verificación de entorno (sin código de negocio)`.

### S2-001 — Event Store mínimo
- **Objetivo:** capacidad Eventos con `append()` · `read()` · `byAggregate()` y almacén mínimo. Sin CQRS/Replay/Projections.
- **Dependencias:** ninguna.
- **Criterios de aceptación:** se publica un evento y se recupera por filtro y por `aggregate`; `append` idempotente (dedupe por `event_id`); no existe ninguna proyección ni replay.
- **Archivos probables:** `gateway/app/capabilities/events/{store.py,models.py,__init__.py}` (nuevo) · migración de tabla · `gateway/tests/test_events_store.py`.
- **Complejidad:** M.
- **Commit:** `feat(events): event store mínimo (append/read/byAggregate)`.

### S2-002 — Catálogo de eventos de Cobranza
- **Objetivo:** definir tipos + criticidad: `pago.iniciado` · `pago.confirmado` · `pago.rechazado` · `factura.pagada` · `servicio.reactivado` (+ alias de los que ya produce Suscripciones).
- **Dependencias:** S2-001.
- **Criterios de aceptación:** cada tipo tiene esquema mínimo y criticidad; `append` rechaza un tipo desconocido.
- **Archivos probables:** `gateway/app/capabilities/events/catalog.py` · `gateway/tests/test_events_catalog.py`.
- **Complejidad:** S.
- **Commit:** `feat(events): catálogo de eventos de cobranza`.

### S2-003 — Ledger: adaptador contable (lectura)
- **Objetivo:** `AccountingAdapter` que lee movimientos normalizados (cargos/pagos/notas) del sistema contable activo (hoy Odoo) por servicio/cliente. **No duplica la contabilidad.**
- **Dependencias:** ninguna (usa `sentinela_api`; agrega endpoints si faltan).
- **Criterios de aceptación:** dado un cliente, devuelve movimientos normalizados; el Ledger no referencia Odoo directo, solo el adaptador.
- **Archivos probables:** `gateway/app/capabilities/ledger/accounting_adapter.py` · `sentinela_api/controllers/ledger.py` (Odoo) · `gateway/tests/test_ledger_adapter.py`.
- **Complejidad:** M.
- **Commit:** `feat(ledger): adaptador contable de lectura + endpoints Odoo`.

### S2-004 — Ledger: Estado de Cuenta
- **Objetivo:** capacidad Ledger que **calcula y sirve el Estado de Cuenta** (saldo · vencido · por vencer) consultando el adaptador. Única fuente del estado de cuenta (sin lógica dispersa).
- **Dependencias:** S2-003.
- **Criterios de aceptación:** Estado de Cuenta correcto por servicio; el cálculo vive solo aquí.
- **Archivos probables:** `gateway/app/capabilities/ledger/service.py` · `gateway/app/routers/ledger.py` · `gateway/tests/test_ledger_estado_cuenta.py`.
- **Complejidad:** M.
- **Commit:** `feat(ledger): estado de cuenta desde el ledger`.

### S2-005 — Puerto PaymentAdapter + Motor de Pago
- **Objetivo:** interfaz `PaymentAdapter` (`authorize`/`confirm`/`refund`-stub) + Motor de Pago que **solo** depende de la interfaz. *Fake adapter* para pruebas. **El Motor nunca referencia Stripe.**
- **Dependencias:** ninguna.
- **Criterios de aceptación:** el Motor autoriza una intención con el *fake*; ninguna importación de Stripe en el Motor.
- **Archivos probables:** `gateway/app/capabilities/payments/{port.py,service.py,fake_adapter.py}` · `gateway/tests/test_payments_port.py`.
- **Complejidad:** M.
- **Commit:** `feat(payments): puerto PaymentAdapter + motor de pago (sin proveedor)`.

### S2-006 — Adaptador Stripe (primer PaymentAdapter)
- **Objetivo:** implementar `PaymentAdapter` con Stripe (crear/autorizar cobro; mapear a {confirmado/en proceso/rechazado}).
- **Dependencias:** S2-005.
- **Criterios de aceptación:** autoriza un cobro en Stripe (modo test); resultado mapeado; claves por configuración (no hardcode).
- **Archivos probables:** `gateway/app/capabilities/payments/stripe_adapter.py` · `gateway/app/config.py` · `gateway/tests/test_payments_stripe.py`.
- **Complejidad:** M.
- **Commit:** `feat(payments): adaptador Stripe (primer PaymentAdapter)`.

### S2-007 — Intención de pago + endpoint (startPayment backend)
- **Objetivo:** crear intención (facturas+monto validados contra el Ledger), iniciar cobro vía Motor, publicar `pago.iniciado`.
- **Dependencias:** S2-005, S2-004, S2-001.
- **Criterios de aceptación:** las facturas pertenecen al cliente y los montos cuadran con el Ledger; se publica `pago.iniciado`; rechazo claro si los montos no cuadran.
- **Archivos probables:** `gateway/app/routers/payments.py` · `gateway/tests/test_payments_intent.py`.
- **Complejidad:** M.
- **Commit:** `feat(payments): intención de pago + endpoint startPayment`.

### S2-008 — Webhook de confirmación → pago.confirmado/rechazado
- **Objetivo:** recibir webhook del proveedor, **verificar firma**, idempotente; publicar `pago.confirmado` o `pago.rechazado`.
- **Dependencias:** S2-006, S2-001.
- **Criterios de aceptación:** firma verificada; webhook duplicado publica el evento **una sola vez**; estados en proceso/rechazado manejados.
- **Archivos probables:** `gateway/app/routers/payments_webhook.py` · `gateway/tests/test_payments_webhook.py`.
- **Complejidad:** M.
- **Commit:** `feat(payments): webhook -> pago.confirmado/rechazado (idempotente)`.

### S2-009 — Aplicación de pago + factura.pagada
- **Objetivo:** consumidor de `pago.confirmado` → registra el pago en el contable (vía adaptador) → marca factura(s) pagada(s) → publica `factura.pagada`. **Conciliación anti doble-pago** (online+OXXO/banco).
- **Dependencias:** S2-008, S2-003.
- **Criterios de aceptación:** se aplica una sola vez; `factura.pagada` emitido; no duplica con un depósito ya conciliado.
- **Archivos probables:** `gateway/app/capabilities/payments/application.py` · `sentinela_api/controllers/payments.py` (aplicar pago) · `gateway/tests/test_payments_application.py`.
- **Complejidad:** L.
- **Commit:** `feat(payments): aplicación de pago + factura.pagada`.

### S2-010 — CFDI async reintetable (consumidor de factura.pagada)
- **Objetivo:** al `factura.pagada` → disparar timbrado CFDI (reusa `sentinela_cfdi_prodigia`), **async y reintetable**; si el PAC falla, el pago **sigue válido** y el CFDI queda pendiente.
- **Dependencias:** S2-009.
- **Criterios de aceptación:** `factura.pagada` → CFDI emitido; fallo de PAC → estado "pendiente reintetable" sin invalidar el pago; reintento exitoso.
- **Archivos probables:** `gateway/app/capabilities/.../cfdi_consumer.py` · Odoo (disparo/estado reintetable) · `gateway/tests/test_cfdi_async.py`.
- **Complejidad:** M.
- **Commit:** `feat(cfdi): timbrado async reintetable al pagar`.

### S2-011 — Reactivation Policy (consumidor de factura.pagada)
- **Objetivo:** evaluar la **Policy** (factura totalmente pagada · servicio suspendido por cobranza · sin otras vencidas) → reactivar el servicio → publicar `servicio.reactivado`. **Por servicio.**
- **Dependencias:** S2-009.
- **Criterios de aceptación:** reactiva **solo** si se cumplen las 3 condiciones; cliente multi-servicio reactiva solo el liquidado; no reactiva si quedan vencidas.
- **Archivos probables:** `gateway/app/capabilities/reactivation/policy.py` · Odoo (reactivar servicio) · `gateway/tests/test_reactivation_policy.py`.
- **Complejidad:** M.
- **Commit:** `feat(reactivation): policy de reactivación por servicio`.

### S2-012 — Notificación de confirmación (consumidor de eventos)
- **Objetivo:** al `pago.confirmado`/`factura.pagada` → notificar al cliente (reusa el canal existente correo/WhatsApp). **No duplica** mensajería.
- **Dependencias:** S2-008/S2-009.
- **Criterios de aceptación:** el cliente recibe confirmación por el canal existente; el consumidor solo reacciona al evento.
- **Archivos probables:** `gateway/app/capabilities/notifications/consumer.py` · adaptadores de canal · `gateway/tests/test_notifications_pago.py`.
- **Complejidad:** S/M.
- **Commit:** `feat(notifications): confirmación de pago`.

### S2-013 — Indicadores MVP (3 consultas)
- **Objetivo:** **cobrado hoy · cartera vencida · pagos pendientes** sobre el Ledger. Sin Dashboard Engine.
- **Dependencias:** S2-004.
- **Criterios de aceptación:** 3 consultas correctas; nada de motor de dashboards.
- **Archivos probables:** `gateway/app/capabilities/ledger/indicators.py` · `gateway/app/routers/ledger.py` · `gateway/tests/test_ledger_indicators.py`.
- **Complejidad:** S.
- **Commit:** `feat(ledger): indicadores MVP (cobrado hoy/cartera/pendientes)`.

### S2-014 — SPA: cablear startPayment() + UX de confirmación
- **Objetivo:** implementar `lib/payments.startPayment()` real → intención → manejar {confirmado/en proceso/rechazado} → confirmación; el Estado de Cuenta se lee del Ledger. Reusa la UX del Sprint 1.
- **Dependencias:** S2-007, S2-009.
- **Criterios de aceptación:** flujo de pago end-to-end en STAGING (test) desde la UX existente; los 3 estados se manejan con mensajes claros; consola limpia.
- **Archivos probables:** `web/lib/payments.ts` · `web/app/(app)/facturacion/page.tsx` · `web/components/PaymentSummaryModal.tsx`.
- **Complejidad:** M.
- **Commit:** `feat(web): pago en línea (startPayment + confirmación)`.

### S2-015 — Pruebas de aceptación de la vertical (E2E)
- **Objetivo:** validar los criterios §12 del spec end-to-end en STAGING + evidencia.
- **Dependencias:** S2-001…S2-014.
- **Criterios de aceptación:** pago→Ledger→`factura.pagada`→CFDI(o pendiente reintetable, pago válido)→Policy reactiva solo si cumple→notificación→Estado de Cuenta desde el Ledger; idempotencia; conciliación; reactivación por servicio; Motor sin Stripe directo. Todo verde.
- **Archivos probables:** `gateway/tests/e2e_sprint2_cobranza.py` · `EVIDENCIA_SPRINT2.md`.
- **Complejidad:** M.
- **Commit:** `test(sprint2): aceptación vertical cobranza + evidencia`.

---

## Resumen
| Capa | Historias |
|---|---|
| Preparación | S2-000 |
| Event Store | S2-001, S2-002 |
| Ledger | S2-003, S2-004, S2-013 |
| Pagos | S2-005, S2-006, S2-007, S2-008, S2-009 |
| Consecuencias (CFDI/Reactivación/Notif) | S2-010, S2-011, S2-012 |
| SPA | S2-014 |
| Aceptación | S2-015 |

**16 historias.** Complejidad: S=5 · M=9 · L=1 (S2-009). Camino crítico: **000**→001→003→004→005→006→007→008→009 → (010‖011‖012) → 014 → 015.
Paralelizable (solo sin dependencia mutua): Event Store (001/002) ∥ Ledger (003/004); CFDI/Reactivación/Notificación (010/011/012) tras 009.

**No escribo código.** Backlog para tu revisión; al aprobarlo, lo commiteo y avanzamos **historia por historia** (cada una con su commit y validación), respetando que el spec no cambia salvo necesidad real aprobada.

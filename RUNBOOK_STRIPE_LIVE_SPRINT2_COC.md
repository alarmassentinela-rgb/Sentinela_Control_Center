# Runbook — 2ª Ventana: Activación de Stripe LIVE (Sprint 2 · Cobranza)

**Estado:** PLAN para tu revisión. **No se configura Stripe LIVE ni se modifica Producción hasta tu autorización + ventana.**
**Contexto:** la **1ª ventana** deja el Sprint 2 desplegado en Producción funcionando con **Stripe TEST** (gateway **0.4.2** con claves test, SPA **0.6.0** con `pk_test`, `sentinela_api` **18.0.0.3.1**, webhook **test**). Esta 2ª ventana hace el **corte a LIVE** (cobros reales), una vez validada la estabilidad.

> **Arquitectura relevante:** el pago del COC usa las claves Stripe del **Gateway** (`COC_STRIPE_*` en su `.env`) y del **SPA** (`NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`, horneada en build). **NO** usa el `payment.provider` nativo de Odoo (id=14, test) → no se toca ese registro. El webhook LIVE llega por `https://api.sentinela.mx/v1/payments/webhook` (ingreso público ya verificado 200; NPM #8 → `:8400`).

---

## 1. Preparación previa (antes de la ventana)
- [ ] **Cuenta Stripe LIVE lista:** identidad/negocio verificados y **payouts a banco configurados** (requisito de negocio para recibir el dinero).
- [ ] **Claves LIVE disponibles:** `sk_live_…`, `pk_live_…` (del dashboard, modo Live).
- [ ] **1ª ventana estable:** Sprint 2 en prod con Stripe test, sin incidencias abiertas; smoke de pago test OK.
- [ ] **Localizar artefactos del gateway prod:** contenedor `gateway-gateway-1` (proyecto compose `gateway`), su `.env` y `docker-compose` (histórico `/opt/sentinela_coc/.env`) — confirmar ruta real en la preparación.
- [ ] **Respaldo del `.env` actual del gateway** (con claves test) → `.env.bak_pre_live_<ts>` (para rollback).
- [ ] **Imágenes de reversión etiquetadas:** SPA test actual `coc-web:0.6.0-test-rollback`; el gateway se revierte por `.env` (no cambia imagen).
- [ ] **Cuenta/tarjeta real** para el cobro mínimo de prueba (preferible una **tarjeta propia** de Sentinela) + una **factura de monto bajo de una cuenta interna/propia** (no de un cliente real).
- [ ] Ventana de bajo tráfico + responsable de guardia + acceso al dashboard de Stripe.

## 2. Registro del webhook LIVE (PRIMERO — genera el `whsec_live`)
> El `whsec` del webhook debe existir antes de configurar el gateway.
1. Dashboard de Stripe → **modo Live** → Developers → Webhooks → **Add endpoint**.
2. **URL:** `https://api.sentinela.mx/v1/payments/webhook`.
3. **Eventos:** `payment_intent.succeeded`, `payment_intent.payment_failed`, `payment_intent.processing`, `payment_intent.canceled`.
4. Guardar → copiar el **Signing secret** (`whsec_live_…`).
- [ ] Endpoint creado en modo **Live**; `whsec_live` copiado (manejar enmascarado, nunca commit).

## 3. Activación de `sk_live` (Gateway) + `pk_live` (SPA)
**Gateway (solo `.env` + restart, sin rebuild):**
1. Editar el `.env` del gateway prod:
   - `COC_STRIPE_SECRET_KEY=sk_live_…`
   - `COC_STRIPE_WEBHOOK_SECRET=whsec_live_…` (del paso 2)
   - `COC_STRIPE_PUBLISHABLE_KEY=pk_live_…` (informativa en el gateway)
2. Recrear/reiniciar `gateway-gateway-1` (misma imagen 0.4.2, misma red/puerto :8400).
- [ ] `/health = 0.4.2`; config Stripe LIVE cargada; **logs sin fuga de secretos**.

**SPA (requiere rebuild — la `pk` se hornea en build):**
1. Build `coc-web:0.6.0-live` con `--build-arg NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_…` + `NEXT_PUBLIC_API_BASE=https://api.sentinela.mx`.
2. Recrear `coc-web-prod` (:3090) con la imagen live. `portal.sentinela.mx` la sirve automáticamente (ingreso ya operativo).
- [ ] `portal.sentinela.mx/login = 200`; el bundle contiene `pk_live` (no `pk_test`).

## 4. Prueba mínima con un COBRO REAL (controlada + reembolsable)
1. Desde `portal.sentinela.mx`, autenticado con una **cuenta interna/propia**, pagar una **factura de monto bajo** (p. ej. el menor adeudo real disponible) con una **tarjeta real propia**.
2. Verificar en la SPA: **"¡Pago confirmado!"**.
3. Verificar el flujo LIVE end-to-end:
   - Stripe dashboard (Live): `PaymentIntent` **succeeded** (id `pi_…`).
   - Webhook LIVE entregado → `[200]` (Developers → Webhooks → intentos).
   - Odoo V18: factura **pagada** (`account.payment` creado); estado de cuenta actualizado; (reactivación si aplicaba).
   - Idempotencia: reenviar el evento desde el dashboard → sin doble aplicación.
4. **REEMBOLSO inmediato** del cobro de prueba (Stripe dashboard → Refund) y **reversa contable en Odoo** (anular/conciliar el pago de prueba) para no dejar el cobro de prueba en la contabilidad real.
- [ ] Cobro real OK · webhook `[200]` · factura pagada · **reembolsado** · reversa contable hecha.

## 5. Validaciones posteriores
- [ ] Un **segundo pago real** de un flujo normal (opcional, si hay un cliente piloto acordado) o confirmación de que el sistema queda listo para cobros reales.
- [ ] Métricas/observabilidad del gateway sin errores; `/metrics` sano.
- [ ] No-regresión del Portal (login, dashboard, facturación-consulta).
- [ ] Alertas (cron alert_checker) operativas.

## 6. Criterios GO / NO-GO
**GO** solo si: webhook LIVE entrega `[200]` + cobro real se aplica correctamente en Odoo + reembolso y reversa OK + idempotencia OK + sin fuga de secretos + Portal sin regresión.
**NO-GO / rollback** si: la firma `whsec_live` no valida (400), el cobro no se aplica, hay doble aplicación, o cualquier inestabilidad del gateway/portal.

## 7. Estrategia de ROLLBACK (de LIVE a TEST, sin downtime del portal)
| Componente | Reversión |
|---|---|
| **Gateway** | Restaurar `.env.bak_pre_live_<ts>` (claves **test**) → reiniciar `gateway-gateway-1`. |
| **SPA** | Recrear `coc-web-prod` desde `coc-web:0.6.0-test-rollback` (bundle con `pk_test`). |
| **Webhook** | Deshabilitar el endpoint **Live** en el dashboard de Stripe (el test sigue por CLI/registro test). |
| **Cobro de prueba** | Ya reembolsado + reversado en Odoo (paso 4). |

> El rollback devuelve el sistema al estado **estable de la 1ª ventana** (Sprint 2 con Stripe test). El Portal permanece arriba en ambos casos (mismo ingreso).

## 8. Evidencia a recopilar (para el acta)
- ID del `PaymentIntent` LIVE (`pi_…`) + captura del cobro **succeeded** en el dashboard.
- Captura del **webhook LIVE** entregado `[200]` (Developers → Webhooks).
- Odoo: factura pagada (id, payment_state) + `account.payment` id; captura del estado de cuenta actualizado.
- ID del **reembolso** (`re_…`) + evidencia de la **reversa contable** en Odoo.
- Logs del gateway (arranque + webhook) **sin secretos**; `/metrics` sano.
- Prueba de **idempotencia** (reenvío sin doble aplicación).
- Confirmación de bundle SPA con `pk_live`.

---

## Resumen de decisiones que requieren tu confirmación antes de la ventana
1. **Cuenta/factura/tarjeta** para el cobro mínimo real (recomiendo cuenta interna/propia + reembolso inmediato).
2. **Momento del corte** a LIVE (tras cuántos días/observaciones de la 1ª ventana en test).
3. Provisión de `sk_live`/`pk_live` (tú) y creación del webhook Live (tú o yo con acceso al dashboard).

> **No se configura Stripe LIVE ni se modifica Producción hasta tu autorización. Este runbook deja preparada la 2ª ventana para la revisión del checklist final de liberación.**

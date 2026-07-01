# Release Notes — Portal COC · Sprint 2 (Vertical Cobranza) · `coc-v1.2.0`

**Fecha objetivo:** (ventana pendiente de autorización) · **RC base:** `coc-v1.2.0-rc4` (`d4427b6`).
**Componentes:** Gateway **0.4.2** · SPA **0.6.0** · `sentinela_api` **18.0.0.3.1**.

## Novedades para el cliente
- **Pago en línea desde el Portal:** el cliente selecciona sus facturas, ingresa su tarjeta (Stripe Elements, seguro — el número de tarjeta no toca nuestros servidores) y **confirma el pago en la misma pantalla**. Ve al instante "¡Pago confirmado!" y su estado de cuenta actualizado.
- **Reactivación automática del servicio** al liquidar el adeudo (cuando el servicio estaba suspendido por cobranza).
- **Estado de cuenta / Ledger** actualizado tras el pago; historial de pagos.

## Cambios técnicos
- **Motor de Pago desacoplado** (`PaymentAdapter`; Stripe = primer adaptador) + **intención de pago** (`/v1/payments/start`) validada contra el Ledger.
- **Webhook idempotente** con verificación de firma (`whsec`) → `pago.confirmado`/`pago.rechazado` → **aplicación contable** en Odoo → `factura.pagada`.
- **CFDI** timbrado async reintetable al pagar (no invalida el pago si el PAC falla).
- **Política de reactivación por servicio** + **notificación** de confirmación (canal existente).
- **SPA:** integración **Stripe.js/Elements**, confirmación en página con manejo de `processing/succeeded/requires_action(3DS)/error`.
- **Gateway:** PaymentIntent con `automatic_payment_methods.allow_redirects='never'` (tarjeta en página, sin redirect).

## Correcciones durante la estabilización del RC (halladas en UAT con Stripe real)
- **UAT-001 (crítico):** metadata de Stripe con `invoice_ids` como lista → todo pago quedaba rechazado. **Corregido** (serialización a string).
- **UAT-002 (crítico):** aplicación del pago fallaba por `AccessError` (`account.payment.register` no honra `sudo` con usuario público). **Corregido** ejecutando el posteo como `SUPERUSER_ID` (decisión controlada Sprint 2; deuda Sprint 3 para usuario técnico dedicado).

## Validación
UAT completa **en verde** con Stripe real (modo test) en STAGING, incluida la confirmación de pago **desde el navegador** (evidencia en `EVIDENCIA_UAT_SPRINT2.md`). Suite gateway 148/8 + e2e §12 7/7; tests `sentinela_api` 0 failed.

## Notas de operación / conocidas
- **Producción requiere Stripe LIVE** (cargos reales) + webhook registrado en `api.sentinela.mx` (ver plan de despliegue §0).
- **OBS-2 (diferida a Sprint 3):** la reactivación ocurre por el hook de `sentinela_subscriptions` antes que la política COC (redundante; sin impacto funcional).
- Sustituir `SUPERUSER_ID` en `apply` por un usuario técnico dedicado (backlog Sprint 3, `MEJORAS_CONTINUAS_COC.md`).

## Compatibilidad / rollback
Aditivo sobre el Sprint 1 (portal de consulta). Rollback por componente disponible (imágenes de reversión + dump V18 + código `sentinela_api` 18.0.0.2.0). Ver `PLAN_DESPLIEGUE_PROD_SPRINT2_COC.md` §5.

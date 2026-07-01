# Evidencia UAT — Sprint 2 (Vertical Cobranza) · Etapa 4

**Fecha:** 2026-06-30 / 2026-07-01 · **Entorno:** STAGING (`Sentinela_STAGING`, odoo-lab :8075 con árbol de addons aislado; gateway :8401; SPA :3080).
**RC bajo prueba:** `coc-v1.2.0-rc1` → (fixes) → **`coc-v1.2.0-rc3`** (NO desplegado a Producción; NO pusheado).
**Integración externa:** Stripe **modo test** (cuenta de `payment.provider` id=14, `livemode=false`); webhooks vía **Stripe CLI** (`stripe listen --forward-to http://127.0.0.1:8401/v1/payments/webhook`), sin exponer el gateway.

---

## 1. Fixture de prueba (datos existentes, no creados)
| Elemento | Valor |
|---|---|
| Cliente | `res.partner` **25735 — ALICIA GUAJARDO** (1 sub, 1 factura abierta) |
| Suscripción | **989 = SUB-0192**, estado inicial **`suspension`** |
| Factura | **90 = INV/2026/00059**, `posted`/`not_paid`, **$400.00 MXN**, vence 2026-05-28 |
| Usuario de auth | Usuario portal **72** (`coc.partner.25735@portal.sentinela.mx`, share=True) — **creado automáticamente** por el flujo de autenticación COC (`_coc_ensure_portal_user`), autorizado como mecanismo estándar; no es dato de negocio. |

## 2. Defectos encontrados y corregidos
### UAT-001 — 🔴 CRÍTICO (RESUELTO en RC2/RC3)
- **Causa:** `/v1/payments/start` pasaba `invoice_ids` como **lista** en `metadata` del PaymentIntent; Stripe exige valores string → `InvalidRequestError` → todo pago quedaba `REJECTED`.
- **Evidencia:** `InvalidRequestError: Metadata values must be strings, but for key 'invoice_ids' you passed a value of type 'hash'`.
- **Fix (mínimo):** serializar `invoice_ids` con `",".join(...)` (gateway `app/routers/payments.py`); gateway `0.4.0→0.4.1`.
- **No detectado antes:** las pruebas usaban `FakeStripe` (no valida tipos de metadata).

### UAT-002 — 🔴 CRÍTICO (RESUELTO en RC3)
- **Causa:** `account.payment.register.action_create_payments()` no honra el flag `su` de `.sudo()` para la escritura de `account.move`; con `auth='public'` el usuario real (uid 4) no tiene permisos de contabilidad → `AccessError`.
- **Evidencia (log Odoo):** `Access Denied by ACLs for operation: write, uid: 4, model: account.move`.
- **Análisis (medido, con rollback):** public+`.sudo()` (uid4/su=True) → **falla**; `with_user(SUPERUSER_ID)` (uid1) → OK; `with_user(usuario contable)` (uid7/su=False) → OK. Determinante = derechos del usuario real, no el flag `su`.
- **Fix (mínimo):** `env = request.env(user=SUPERUSER_ID)` (sentinela_api `controllers/payments.py`); addon `18.0.0.3.0→3.1`. **Decisión controlada Sprint 2** (no había usuario técnico con permisos de contabilidad); **deuda Sprint 3** registrada en `MEJORAS_CONTINUAS_COC.md` (sustituir por usuario técnico dedicado).

## 3. Validación técnica del RC3
- Gateway 0.4.1: suite **148 passed / 8 skipped** + e2e §12 **7/7** (imagen fresca).
- sentinela_api 18.0.0.3.1: `-u` limpio + tests del addon **0 failed / 0 error** (19 tests).
- PROD intacto durante toda la UAT: `sentinela_api 18.0.0.2.0`, `/health :8070 = 200`, árbol de addons compartido sin cambios (aislamiento por `staging-addons`).

## 4. Resultado por escenario (RC3 — re-ejecutados todos)
| # | Escenario | Resultado | Evidencia |
|---|---|:--:|---|
| 1 | Pago exitoso (SPA→start) | ✅ PASS | `/v1/payments/start`→PI `processing`; `confirm(pm_card_visa)`→`succeeded` |
| 2 | Recepción webhook | ✅ PASS | listener→`[200]`; `pago.confirmado` en Event Store |
| 3 | Validación firma `whsec` | ✅ PASS | válida OK (caso 2); inválida→`400 invalid_signature` |
| 4 | Aplicación en Odoo | ✅ PASS | factura 90→`paid`; `account.payment` creado ($400) |
| 5 | Registro en Ledger | ✅ PASS | statement balance 400→**0** |
| 6 | Reactivación del servicio | ✅ PASS* | sub 989→**`active`** (vía hook de `sentinela_subscriptions`, ver OBS-2) |
| 7 | Generación de eventos | ✅ PASS* | `pago.iniciado`→`pago.confirmado`→`factura.pagada` |
| 8 | Estado de cuenta actualizado | ✅ PASS | balance 0, overdue 0 |
| 9 | Idempotencia (reenvío webhook) | ✅ PASS | `stripe events resend`→`[200]` sin doble aplicación (1 pago, 1 `factura.pagada`) |
| 10 | Pago rechazado | ✅ PASS | `pm_card_chargeDeclined`→`CardError`→`pago.rechazado`, sin aplicar |
| 11 | Cancelación | ✅ PASS | `PaymentIntent.cancel`→`canceled`→IGNORED, sin aplicar |
| 12 | Sin regresiones | ✅ PASS | suite 148/8 + e2e 7/7 + tests addon 0 failed |

## 5. Observaciones
- **OBS-1 (BLOQUEANTE del RC):** la SPA **no implementa confirmación client-side** (sin `@stripe/*`, sin uso del `client_secret`). `PaymentSummaryModal.pay()` llama `startPayment()` y solo muestra el estado; el PaymentIntent queda en `requires_payment_method`. **Un cliente real no puede completar el pago desde el Portal.** En la UAT se simuló la confirmación server-side. Análisis de alcance en documento aparte.
- **OBS-2 (Sprint 3, aceptada):** el servicio se reactiva vía el hook propio de `sentinela_subscriptions` (`_compute_payment_state`→`action_reactivate` al marcarse pagada) **antes** que la política COC → la política COC devuelve `no_suspendido` (redundante). Objetivo cumplido; decidir dueño de la reactivación en Sprint 3.
- **(Menor)** el adaptador crea el PaymentIntent sin `automatic_payment_methods[allow_redirects]='never'` → habilita métodos con redirect (exige `return_url` al confirmar). Relacionado con OBS-1.

## 6. Estado final del fixture
`inv90 = paid (residual 0)` · `sub989 = active` · `account.payment(25735) = 1 ($400)` · usuario portal 72. Reproducible: restaurar `DB_Sentinela_STAGING_PREDEPLOY_SPRINT2_20260630_1612.dump` devuelve el fixture a su estado inicial.

## 7. Conclusión
Los **rieles backend de la vertical Cobranza** (pago→webhook→firma→aplicación→ledger→reactivación→idempotencia→rechazo→cancelación) están **validados end-to-end con Stripe real y correctos**; los dos defectos críticos (UAT-001, UAT-002) quedaron corregidos y verificados. **El RC NO se aprueba para Producción** por **OBS-1** (falta la confirmación de pago en la SPA para que un cliente complete el cobro). UAT **abierta**.

---

# Addendum — Ciclo RC4 (cierre de OBS-1: confirmación de pago en la SPA)

**RC:** `coc-v1.2.0-rc4` (commit `d4427b6`; NO pusheado). Cambios: SPA **0.6.0** (Stripe.js/Elements: `lib/stripe.ts`, `components/CardPaymentForm.tsx`, `PaymentSummaryModal` con confirmación en página, deps `@stripe/*`, `Dockerfile` ARG pk) + Gateway **0.4.2** (PaymentIntent con `automatic_payment_methods.allow_redirects='never'` → tarjeta en página, sin `return_url`; resuelve la observación menor). sentinela_api sin cambios (18.0.0.3.1).

## Validación técnica RC4
- Gateway 0.4.2: suite **148/8** + e2e §12 **7/7** (imagen fresca).
- SPA 0.6.0: `tsc --noEmit` **OK** + `next build` **OK** (Docker); pk baked en el bundle.
- sentinela_api 18.0.0.3.1: `-u` limpio tras restaurar el dump; tests del addon **0 failed / 0 error**.

## UAT completa re-ejecutada desde el escenario 1 (fixture restaurado del dump)
Rieles backend (driver): escenarios **1,2,3,4,5,8,9,10,11 = PASS**; **6/7** = comportamiento OBS-2 aceptado (la sub se reactiva vía hook de `sentinela_subscriptions`; `sub989 → active`).

### Escenario 1 — Pago exitoso DESDE LA SPA (navegador real, Stripe Elements) ✅ PASS
Prueba con navegador (puppeteer + Chrome), fixture limpio (inv90 `not_paid`, sub989 `suspension`):
1. Autenticación (sesión portal 25735) → `/facturacion`.
2. Selección de la factura INV/2026/00059 → "Continuar" → "Pagar".
3. **Stripe PaymentElement renderizado** en la SPA (captura `spa_payment_element.png`: campos reales Card number / Expiration / CVC / Country).
4. Captura de tarjeta de prueba **4242 4242 4242 4242** en el iframe de Stripe → submit.
5. `stripe.confirmPayment` → **`succeeded`** → webhook real `payment_intent.succeeded` → `[200]`.
6. **UI: "¡Pago confirmado! Tu estado de cuenta ya está actualizado."** (captura `spa_payment_result.png`).
7. **Efecto en Odoo:** `inv90 → paid` (residual 0) · `account.payment = 1 ($400)` · `sub989 → active`.

**Evidencia visual:** `spa_payment_element.png` (formulario de tarjeta), `spa_payment_result.png` (confirmación).

## Conclusión RC4
**OBS-1 RESUELTO y verificado end-to-end.** Un cliente completa un pago en línea desde el Portal (captura de tarjeta en Stripe Elements → confirmación en página → factura pagada + servicio reactivado). Los dos defectos críticos previos (UAT-001, UAT-002) permanecen resueltos. **UAT completa EN VERDE.** OBS-2 diferida a Sprint 3 (aceptada). RC4 sin push, a la espera de re-evaluación de aprobación para Producción.

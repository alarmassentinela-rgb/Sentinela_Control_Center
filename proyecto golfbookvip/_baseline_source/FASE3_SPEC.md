# FASE 3 — Integridad de dinero (transaccional + idempotencia Stripe)

> Contrato para Codex. Toca DINERO REAL (saldos de socios + facturación Stripe). El Arquitecto verifica
> en staging con test de CONCURRENCIA real y replay de eventos Stripe. NO tocar frontend. NO tocar producción.
> Alcance acotado a los CRÍTICOS + wins claros; `balances.py` (proyección de apuestas) y columna `currency`
> quedan para Fase 3B.

## Contexto (hallazgos a cerrar)
- **C1 (doble gasto):** `_apply_transaction` (`clubs.py:~2010`) hace read-modify-write del balance SIN lock
  (`new_balance = float(acc.balance) + delta; acc.balance = new_balance`). Dos cargos concurrentes leen el
  mismo balance y el último gana → rebasa `credit_limit` y descuadra balance vs ledger.
- **C3 (float en dinero):** `float(acc.balance)` degrada el `Decimal` que ya devuelve la columna `Numeric`.
  `ChargePayload.amount`/`PaymentPayload.amount` son `float`. La aritmética de saldo real debe ser `Decimal`.
- **C2 (webhooks Stripe sin idempotencia):** `Invoice.stripe_invoice_id` sin UNIQUE y ningún handler dedup
  por `event["id"]`. Stripe reintenta → Invoices duplicadas → revenue doble. Además
  `payment_intent.succeeded` guarda el id del PaymentIntent en `stripe_invoice_id`.
- **A3 (factura de club huérfana):** `_handle_invoice_paid` solo busca en `UserSubscription`, nunca en
  `ClubSubscription` → `user_id`/`club_id` quedan NULL y el club sigue `past_due` pese a pagar.
- **M1 (auto-cobro de booking no idempotente):** `_post_booking_fees` (`clubs.py:~1530`) no verifica si ya
  existe el `green_fee` para ese player (a diferencia del refund, que sí dedup por `reference_id`).

## Entregables

### 1. C1 — Lock de fila en `_apply_transaction`
- Al inicio de `_apply_transaction`, RE-CARGA la cuenta con lock de fila:
  `locked = await db.execute(select(MemberAccount).where(MemberAccount.id == acc.id).with_for_update());
  acc = locked.scalar_one()`. Lee el balance de esa instancia bloqueada. Así dos cargos concurrentes se
  serializan y el segundo ve el balance ya actualizado.
- Mantén la validación de `credit_limit` DESPUÉS de tomar el lock (con el balance fresco).

### 2. C3 — `Decimal` en el camino de dinero real
- En `_apply_transaction`: opera con `Decimal`. `acc.balance` ya es `Decimal` (columna Numeric); NO lo pases
  por `float()`. Convierte `amount` a `Decimal(str(amount))` y cuantiza a 2 decimales
  (`.quantize(Decimal("0.01"))`). `new_balance` y `balance_after` en `Decimal`.
- Cambia `ChargePayload.amount` y `PaymentPayload.amount` (y cualquier payload de dinero de cuenta de socio)
  de `float` a `condecimal(max_digits=12, decimal_places=2, gt=0)` (o `Decimal` con validación > 0).
- En `stripe_webhook.py`: la conversión `amount/100` debe ser `Decimal`:
  `(Decimal(pi["amount"]) / Decimal(100)).quantize(Decimal("0.01"))` (idem `amount_paid`). NO uses float.
- NO conviertas `balances.py` en esta fase (es proyección de apuestas recomputable; va en 3B).

### 3. C2 — Idempotencia de webhooks Stripe (requiere MIGRACIÓN)
- Nuevo modelo `ProcessedStripeEvent` (`app/models/payment.py`): tabla `processed_stripe_events` con
  `event_id: str PK` (varchar 200) y `processed_at: timestamptz server_default now()`. Regístralo en
  `app/models/__init__.py`.
- Agrega `UniqueConstraint` a `Invoice.stripe_invoice_id` (nombre explícito, p.ej.
  `uq_invoices_stripe_invoice_id`). NOTA: permite múltiples NULL (Postgres lo hace por defecto).
- Genera la migración Alembic `0003_stripe_idempotency` DESDE los modelos (`alembic revision --autogenerate`),
  revisando que solo cree la tabla nueva + el unique (ignora el ruido conocido de `player_hole_stats`
  documentado en `alembic/README.md`). Deja `down_revision = "0002_seed_plans"`.
- En `stripe_webhook.py`, al inicio del handler: si `event["id"]` ya existe en `processed_stripe_events`,
  responde `{"status":"duplicate"}` SIN procesar. Si no, insértalo (dentro de la misma transacción) y procesa.
- En los `INSERT` de `Invoice`, usa `ON CONFLICT (stripe_invoice_id) DO NOTHING` (o captura IntegrityError)
  para que un reintento no duplique.
- Corrige el nombre engañoso: en `_handle_payment_intent_succeeded`, el `stripe_invoice_id` NO debe recibir el
  id del PaymentIntent; usa un campo/valor coherente (p.ej. deja `stripe_invoice_id=None` y guarda el PI id en
  `description`, o añade lógica clara). Documenta la decisión.

### 4. A3 — `invoice.paid` atribuye club
- En `_handle_invoice_paid`: si no se encontró `UserSubscription` por `stripe_sub_id`, busca en
  `ClubSubscription`; si existe, setea `club_id = sub.club_id`, `sub.status = "active"`, y la Invoice con
  `club_id`. Réplica del patrón que ya usa `_handle_subscription_updated`.

### 5. M1 — Idempotencia del auto-cobro de booking
- En `_post_booking_fees`, antes de postear el `green_fee` de cada player, verifica si YA existe un
  `AccountTransaction` con `reference_type="tee_time_booking_player"` y `reference_id=player.id`; si existe,
  omítelo (no recargar). Igual que hace `_refund_booking_fees`.

### 6. Helper de reconciliación (chequeo de cuadre)
- Agrega una función util (p.ej. en `app/services/balances.py` o un `app/services/accounts.py` nuevo) que,
  dada una `account_id`, calcule el saldo esperado sumando los deltas firmados de sus `AccountTransaction`
  (derivando el signo de `type` con `CHARGE_TYPES`/`CREDIT_TYPES`, "other" con su signo) y lo compare con
  `MemberAccount.balance`. Devuelve `(ok: bool, expected, actual)`. Es para diagnóstico/tests, no un endpoint.

## Verificación que el Arquitecto correrá (no la simules)
- **C1**: test de concurrencia real (N cargos simultáneos sobre una cuenta con credit_limit) → balance final
  correcto y ningún cargo rebasa el límite; balance == suma de deltas del ledger.
- **C2**: replay del mismo `event.id`/misma invoice → una sola fila `Invoice`; segundo POST → "duplicate".
- **C3**: un split/carga que en float perdería un centavo → cuadra exacto.
- **A3/M1**: unit/integration en staging.
- **Migración**: `alembic upgrade head` limpio en BD vacía + autogenerate vacío (salvo el quirk conocido).

## Reglas
- Backend only: `clubs.py`, `stripe_webhook.py`, `models/payment.py`, `models/__init__.py`,
  `alembic/versions/0003_*`, `schemas`/payloads de dinero, y el helper de reconciliación. NO frontend,
  NO `balances.py` (salvo el helper), NO otras migraciones.
- No inventes verificación. Entrega diffs resumidos, el contenido de la migración 0003, y la decisión sobre
  el `stripe_invoice_id` del PaymentIntent.

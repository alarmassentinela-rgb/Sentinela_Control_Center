# FASE 4B — Billing/upgrade: Stripe Checkout + webhook de activación de plan + UI

> Contrato para Codex. Convierte el muro `402 plan_limit` (Fase 4A) en un pago real. Stripe está en modo
> TEST (`rk_test_`). NO requiere migración (plan_id/plan_expires_at/user_subscriptions/club_subscriptions
> ya existen). El Arquitecto verifica en staging con MOCKS deterministas (sin llamar a Stripe real).
> NO tocar saldos (Fase 3), NO tocar el enforcement (Fase 4A, ya vive).

## Contexto
- Fase 4A ya expone `GET /billing/plans`, `GET /users/me/plan`, `GET /clubs/{id}/plan` y lanza
  `402 {code:"plan_limit", resource, current, limit, upgrade_to}` al exceder límites.
- Modelos: `User.plan_id/plan_expires_at`; `Club.plan_id/plan_expires_at/stripe_customer_id`;
  `UserSubscription`/`ClubSubscription` (plan_id, status, stripe_sub_id, current_period_start/end).
- Webhook (`stripe_webhook.py`) ya dedup por `event["id"]` (Fase 3, `processed_stripe_events`) y maneja
  subscription.updated/deleted, invoice.paid/payment_failed. FALTA `checkout.session.completed`.
- `dateutil.relativedelta` está disponible (python-dateutil en requirements).

## BACKEND

### 1. `app/core/config.py`
- Agrega `FRONTEND_URL: str = "https://golfbookvip.com"` (para success/cancel URLs).

### 2. `POST /billing/checkout` (en `app/api/v1/billing.py`)
- Body: `{ "plan_code": str, "cycle": "monthly"|"yearly", "club_id": uuid | null }`.
- Resolver el plan por `code` (activo). Rechazos:
  - plan inexistente/inactivo → 404.
  - plan con precio 0 (free_*) o precio del ciclo == 0 → 400 "Ese plan no requiere pago".
- Alcance:
  - Si `plan.plan_type == "club"`: `club_id` obligatorio y `await _require_club_role(db, club_id, current_user, "admin")`. scope="club".
  - Si `plan.plan_type == "player"`: scope="user" sobre `current_user`.
- Crear Stripe Checkout Session (`stripe.checkout.Session.create`):
  - `mode="subscription"`.
  - `line_items=[{"price_data": {"currency": (club.currency.lower() if club else "usd"),
    "product_data": {"name": plan.name}, "unit_amount": int(precio_del_ciclo * 100),
    "recurring": {"interval": ("year" if cycle=="yearly" else "month")}}, "quantity": 1}]`.
  - `customer_email = current_user.email`.
  - `metadata = {"scope": scope, "user_id": str(current_user.id), "club_id": str(club_id) if club_id else "",
    "target_plan_id": str(plan.id), "target_plan_code": plan.code, "cycle": cycle}`.
  - `success_url = f"{settings.FRONTEND_URL}/es/billing?status=success&session_id={{CHECKOUT_SESSION_ID}}"`,
    `cancel_url  = f"{settings.FRONTEND_URL}/es/billing?status=cancel"`.
  - `client_reference_id = str(current_user.id)`.
- Devolver `{ "checkout_url": session.url }`. Rate-limit razonable (p.ej. 20/min).
- Envuelve el create en try/except de `stripe.error.StripeError` → 502 con mensaje claro (sin filtrar secretos).

### 3. Webhook `checkout.session.completed` (en `stripe_webhook.py`)
- Añade la rama `elif event_type == "checkout.session.completed":` que llame a un handler nuevo.
- Handler `_handle_checkout_completed(db, session)`:
  - Lee `session["metadata"]`. Si falta `target_plan_id` → return (no es nuestro).
  - `plan_id = int(target_plan_id)`; `cycle`; `scope`.
  - `expires = datetime.now(tz=utc) + relativedelta(years=1 if cycle=="yearly" else months=1)`.
  - Si scope=="club": set `Club.plan_id=plan_id`, `Club.plan_expires_at=expires`,
    `Club.stripe_customer_id = session.get("customer")`; upsert `ClubSubscription`
    (plan_id, status="active", stripe_sub_id=session.get("subscription"),
    current_period_start=now, current_period_end=expires).
  - Si scope=="user": set `User.plan_id=plan_id`, `User.plan_expires_at=expires`; upsert `UserSubscription`
    (idem).
  - Idempotente: el dedup por event.id ya lo cubre; además el upsert por stripe_sub_id no debe duplicar.
- Añade `checkout.session.completed` a la lista del docstring.

### 4. Downgrade al cancelar (`subscription.deleted`)
- En `_handle_subscription_deleted`, además de marcar `status="cancelled"`, revierte el plan al gratis:
  - user_sub → `User.plan_id = (SELECT id FROM subscription_plans WHERE code='free_player')`, plan_expires_at=None.
  - club_sub → `Club.plan_id = free_club`, plan_expires_at=None.
  (Reutiliza un helper `_free_plan_id(db, plan_type)`.)

## FRONTEND

### 5. Página `/[locale]/billing/page.tsx`
- Client component. Al montar: `GET /users/me/plan` (plan del jugador + uso). Si el usuario administra un club
  (query `?club_id=` o el club del contexto), también `GET /clubs/{club_id}/plan`. Y `GET /billing/plans`.
- Renderiza: plan actual + barras de uso (grupos, historial / socios, canchas); y las tarjetas de planes
  superiores con precio mensual/anual y botón "Subir a {nombre}".
- Al pulsar upgrade: `POST /billing/checkout {plan_code, cycle, club_id?}` → `window.location.href = checkout_url`.
- Maneja el retorno: si `?status=success` muestra banner "¡Plan activado!" y refresca el uso; si `?status=cancel`
  muestra "Pago cancelado".
- Añade un enlace "Planes/Facturación" en el menú (Navbar) y/o en `/profile`.

### 6. Captura global del 402 plan_limit (`src/lib/api.ts`)
- En el interceptor de respuesta, si `err.response?.status === 402` y `data.detail?.code === "plan_limit"`:
  no reintentar; redirige a `/{locale}/billing?limit={resource}` (o dispara un evento que un handler global
  muestre como modal "Límite alcanzado — sube de plan"). Mantén intacto el manejo de 401 (Fase 2B).

## Verificación que el Arquitecto correrá (mocks, sin Stripe real)
- `/billing/checkout` con `stripe.checkout.Session.create` monkeypatcheado → asserts: metadata correcta,
  `unit_amount = precio*100`, `mode="subscription"`, interval según cycle, devuelve checkout_url;
  club plan por no-admin → 403; plan free → 400.
- `_handle_checkout_completed` con evento mock (club y user) → `plan_id`/`plan_expires_at` seteados +
  subscription creada; replay del mismo event.id → idempotente (sin doble).
- `subscription.deleted` → plan revertido a free_*.
- Frontend: `next build`.
(El E2E real en Stripe test — checkout redirect + webhook por Stripe CLI — queda como smoke manual con la
`sk_test`/`rk_test` con scope de Checkout; documentarlo, no simularlo.)

## Reglas
- Backend: `config.py`, `billing.py`, `stripe_webhook.py`. Frontend: `billing/page.tsx` (nuevo), `lib/api.ts`,
  Navbar/profile (enlace). NO migraciones, NO tocar saldos ni el enforcement de 4A. Entrega diffs resumidos,
  el shape del body de `/billing/checkout`, y la lista de eventos webhook soportados tras el cambio.

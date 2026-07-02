# FASE 4A — Motor SaaS free-tier: enforcement de planes + visibilidad de uso

> Contrato para Codex. Modelo de negocio: **Jugador gratis / Club de pago**. Los 6 planes YA existen en prod
> (seed 0002) con sus límites, pero NO se aplican en ningún lado. Esta fase los ENFORZA y expone el uso.
> Backend only. El Arquitecto verifica en staging (script de límites real). NO tocar producción, dinero de
> saldos, ni el flujo Stripe de pago (eso es Fase 4B).

## Planes y límites (de la tabla subscription_plans en prod)
| code | tipo | max_members | max_courses | max_groups | max_rounds_history |
|---|---|---|---|---|---|
| free_player | player | — | — | **1** | **20** |
| player_pro | player | — | — | — (ilimitado) | — |
| free_club | club | **30** | **1** | — | — |
| club_starter | club | 100 | 2 | — | — |
| club_pro | club | 500 | — | — | — |
| club_enterprise | club | — | — | — | — |
`NULL` en un límite = ilimitado. Un usuario sin `plan_id` = **free_player**; un club sin `plan_id` = **free_club**.

## Hechos del modelo (verificados)
- `Course.club_id` (nullable) → max_courses se cuenta por club.
- `Group.created_by` = dueño → max_groups se cuenta por usuario (grupos que creó).
- `ClubMember.status == "active"` → max_members cuenta socios activos del club.
- Altas de socio (todas deben enforzar): self-join (`clubs.py:~282`), `add_member_to_padron` (`~659/698`),
  import masivo CSV (`~868`), y registro con `club_code` en `auth.py::register`.
- `User.plan_id` / `Club.plan_id` FK a `subscription_plans.id` (Integer). Hoy quedan NULL al crear.

## Entregables

### 1. Servicio de planes (`app/services/plans.py`)
- Constantes `FREE_PLAYER_CODE="free_player"`, `FREE_CLUB_CODE="free_club"`.
- `async def get_user_plan(db, user) -> SubscriptionPlan`: por `user.plan_id`; si NULL o expirado
  (`user.plan_expires_at` pasado), devuelve el plan `free_player`.
- `async def get_club_plan(db, club) -> SubscriptionPlan`: por `club.plan_id`; si NULL/expirado → `free_club`.
- Helper de error uniforme `plan_limit_error(code, current, limit, upgrade_hint)` que lanza
  `HTTPException(status_code=402, detail={"code":"plan_limit","resource":code,"current":current,"limit":limit,
  "message": "...", "upgrade_to": upgrade_hint})`.
- Enforcers (lanzan 402 si se excede; no-op si el límite es NULL):
  - `async def enforce_club_member_limit(db, club)`: cuenta ClubMember activos; si `>= max_members` → error
    (upgrade_hint: siguiente plan de club, p.ej. free_club→club_starter→club_pro).
  - `async def enforce_club_course_limit(db, club_id)`: cuenta Course con ese club_id; si `>= max_courses` → error.
  - `async def enforce_user_group_limit(db, user)`: cuenta Group con `created_by=user.id`; si `>= max_groups` → error.
- `async def usage_for_user(db, user) -> dict` y `usage_for_club(db, club) -> dict`: devuelven plan + uso vs límite
  (para los endpoints de visibilidad).

### 2. Aplicar enforcement
- `groups.py::create_group`: `await enforce_user_group_limit(db, current_user)` antes de crear.
- `courses.py::create_course`: si `data.club_id` no es None, `await enforce_club_course_limit(db, data.club_id)`
  antes de crear.
- Altas de socio — llama `await enforce_club_member_limit(db, club)` antes de crear el `ClubMember` en:
  self-join (`clubs.py`), `add_member_to_padron`, import masivo CSV, y `auth.py::register` (rama club_code —
  ahí, si se excede el límite, NO agregues el socio pero NO falles el registro: registra al usuario y omite el
  vínculo, devolviendo el warning como ya se hace con código inválido).
- `rounds.py::list_my_rounds` (y cualquier listado de "mis rondas"/historial): limita el número de resultados a
  `get_user_plan(...).max_rounds_history` cuando no sea NULL (cap de retención visible para free_player=20).
  Es un cap de LECTURA, no bloquees crear rondas.

### 3. Endpoints de visibilidad
- `GET /users/me/plan` (en `users.py`): `usage_for_user` del `current_user` (plan actual + grupos usados/límite +
  cap de historial).
- `GET /clubs/{club_id}/plan` (en `clubs.py`): `usage_for_club` (requiere ser miembro o staff del club); plan +
  socios usados/límite + canchas usadas/límite.
- Nuevo router `app/api/v1/billing.py` con `GET /billing/plans`: lista los planes activos (separados player/club:
  code, name, price_monthly, price_yearly y límites) para la UI de upgrade. Regístralo en `router.py` con prefix
  `/billing`. (El checkout/pago real es Fase 4B; aquí solo se listan.)

## Verificación que el Arquitecto correrá (no la simules)
Script en staging: club con plan free_club (max_members=30, max_courses=1) → agregar 30 socios OK, el 31 → 402;
crear 1 cancha del club OK, la 2ª → 402. Usuario free_player → crear 1 grupo OK, el 2º → 402. Cambiar el club a
club_pro (max_members=500) → el socio 31 ahora pasa. Endpoints /users/me/plan y /clubs/{id}/plan devuelven el uso
correcto. /billing/plans lista los 6.

## Reglas
- Backend only: `services/plans.py` (nuevo), `groups.py`, `courses.py`, `clubs.py`, `auth.py`, `rounds.py`,
  `users.py`, `billing.py` (nuevo), `router.py`. NO frontend, NO migraciones (los planes ya existen), NO Stripe
  de pago, NO tocar la lógica de saldos de Fase 3.
- Entrega: diffs resumidos, lista de los puntos de alta de socio donde pusiste el enforcement, y el shape JSON de
  `/users/me/plan` y `/clubs/{id}/plan`.

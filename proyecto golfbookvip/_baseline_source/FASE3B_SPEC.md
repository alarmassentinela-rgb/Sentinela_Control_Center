# FASE 3B — Decimal en balances.py + invariante suma-cero + currency en cuentas

> Contrato para Codex. Cierra los últimos puntos contables de la auditoría (C3 en balances, M2, A2).
> `balances.py` está VIVO en prod (feature breakdown) → convertir a Decimal SIN cambiar la lógica de reparto
> ni los textos del breakdown. El Arquitecto verifica en staging (suma-cero real + migración). NO tocar
> el enforcement de planes, ni Stripe, ni _apply_transaction (ya quedó en Decimal en Fase 3).

## Contexto
- `app/services/balances.py` (P&L de apuestas, proyección recomputable vía `persist_balances` delete+insert)
  usa float en ~48 sitios: `_split`, `float(bc.xxx)`, `pot = fee*n`, `pot*share`, `pot/len(winners)`, etc.
- Los textos del breakdown usan `f"${x:.2f}"` → funcionan igual con Decimal (no cambiarlos).
- `MemberAccount` y `AccountTransaction` NO tienen columna `currency`; `Club.currency` sí existe (default en el
  modelo, prod usa "MXN"/"USD"). `_apply_transaction` ya opera en Decimal (Fase 3).
- Ya existe `app/services/accounts.py::reconcile_account_balance` (Fase 3).

## Entregables

### 1. `balances.py` → Decimal (C3) — preservando comportamiento
- Cambia TODO el camino de dinero a `decimal.Decimal`:
  - `_split(amount, n)`: firma y retorno en `Decimal`; reparte en cents sin perder residuo (ver punto 2).
  - Reemplaza `float(bc.<campo>)` por `Decimal(str(bc.<campo> or 0))`.
  - `pot`, `share`, `prize`, `prize_each`, `per_hole`, `penalty`, `amount`, y los montos por jugador en `Decimal`.
    Cuantiza a cents (`.quantize(Decimal("0.01"))`) los montos FINALES por jugador (lo que se acumula en
    `amounts_paid`/totales). Intermedios pueden quedar en Decimal sin cuantizar.
  - Los `share` (0.60/0.30/0.10) como `Decimal("0.60")` etc.
- NO cambies: la lógica de ganadores/empates, los rangos de hoyos, los textos ES/EN del breakdown, ni las
  claves del dict de salida. Solo el tipo numérico.
- El dict devuelto por `compute_balances` puede contener Decimals; FastAPI los serializa vía jsonable_encoder
  (a número). Asegura que los totales por jugador sean Decimal cuantizado a 2 decimales.

### 2. Invariante suma-cero (M2)
- En los pools "todos-pagan / ganador-recibe" (entry_fee, nassau, per_hole, prize_event, three_putt), la suma de
  los deltas de todos los jugadores debe ser 0. Los skins con forfeit (documentado) destruyen dinero a propósito.
- Al final de `compute_balances`, calcula `total = sum(player_totals)` y `total_forfeited` (lo destruido por
  skins forfeit). Si `abs(total + total_forfeited) > Decimal("0.01")`, haz `logging.warning(...)` con el round_id
  y los montos (NO lances excepción — es un guard de observabilidad, no debe romper el endpoint).
- Para que el reparto cuadre exacto, en `_split`/repartos con residuo (p.ej. pot/3), asigna el residuo de cents al
  primer ganador (patrón "largest remainder") para que Σ = pot exactamente. Documenta esto en un comentario.

### 3. Currency en cuentas de socio (A2) — migración 0004
- Modelos (`app/models/club.py`): agrega `currency: Mapped[str] = mapped_column(String(10), nullable=True)` a
  `MemberAccount` y a `AccountTransaction`.
- Migración `0004_account_currency` (autogenerada desde modelos; `down_revision="0003_stripe_idempotency"`):
  - `add_column` currency en `member_accounts` y `account_transactions`.
  - Backfill: `UPDATE member_accounts a SET currency = c.currency FROM clubs c WHERE a.club_id=c.id AND a.currency IS NULL;`
    y `UPDATE member_accounts SET currency='USD' WHERE currency IS NULL;`
    `UPDATE account_transactions t SET currency = a.currency FROM member_accounts a WHERE t.account_id=a.id AND t.currency IS NULL;`
    `UPDATE account_transactions SET currency='USD' WHERE currency IS NULL;`
  - (Ejecuta los backfills con `op.execute(...)` dentro del upgrade, tras los add_column.)
- Wiring en `clubs.py`:
  - `_get_or_create_account`: setea `currency = club.currency` (carga el club; default "USD" si nulo).
  - `_apply_transaction`: stampa `tx.currency = acc.currency`.
  - Ignora el ruido conocido de `player_hole_stats` en el autogenerate (ver `alembic/README.md`).

### 4. (A1) NO reescribir el signo del ledger
- NO cambies la convención de `amount` (abs + type) — reescribir dinero histórico es riesgoso y `reconcile_account_balance`
  ya reconstruye el saldo desde el ledger firmado por tipo. Deja A1 cubierto por ese helper; no lo toques.

## Verificación que el Arquitecto correrá (no la simules)
- **balances Decimal + suma-cero:** crear un round con 3 jugadores + `entry_fee` + scores mínimos; `compute_balances`
  → los totales por jugador son `Decimal` cuantizado y `sum(totales) == 0` exacto (sin forfeits). Grep: 0
  `float(` en el camino de dinero de balances.py.
- **currency:** `alembic upgrade head` aplica 0004 limpio; `member_accounts`/`account_transactions` tienen
  `currency`; una cuenta nueva de un club MXN queda en MXN y su transacción también; autogenerate vacío (salvo quirk).

## Reglas
- Backend: `app/services/balances.py`, `app/models/club.py`, `alembic/versions/0004_*`, `app/api/v1/clubs.py`
  (solo `_get_or_create_account` y el stamp de currency en `_apply_transaction`). NO frontend, NO Stripe, NO
  enforcement de planes. Entrega diffs resumidos, el contenido de 0004, y confirma que no quedó `float(` de dinero
  en balances.py.

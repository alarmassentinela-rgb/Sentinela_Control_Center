# Resumen de sesión — 2 de julio de 2026

## GolfBookVIP — Auditoría profunda + 7 fases de endurecimiento + despliegue a producción

Sesión maratónica dirigiendo a **Codex** (Arquitecto=Claude diseña contrato → Codex ejecuta → revisión
línea por línea → **verificación contra Postgres/Docker reales** → commit scoped → cherry-pick golf-only a
`main`). Todo desplegado y verificado en producción (`golfbookvip.com`).

Los contratos de cada fase quedaron en `_baseline_source/FASE*_SPEC.md` (útiles para retomar).

---

## 1. Auditoría (12 hallazgos por severidad)
Barrido con agentes paralelos (autz/multitenencia, dinero/saldos, frontend) + lectura del núcleo.
Críticos: esquema irreproducible, reset-token regalado, IDOR de rondas (`invite_player`), JWT en localStorage.
Altos: doble gasto en saldos, float en dinero, webhooks Stripe sin idempotencia, Redis muerto (WS en-memoria).

## 2. Fases (todas en prod, cada commit toca SOLO `proyecto golfbookvip/`)

| Fase | Commit `main` | Qué cerró | Verificación real |
|---|---|---|---|
| **1** | `481d1cf` | Alembic baseline (0001) desde dump vivo + seed planes (0002) + `RoundTeam` + docker-compose.staging | 43 tablas idénticas a prod en Docker |
| **2A** | `6061094` | reset por email (no en JSON), `require_round_creator/viewer` en rounds.py, `_require_club_role` en members, rate-limit slowapi | 7/7 pruebas de seguridad en staging |
| **2B** | `46f7886` | refresh token en cookie httpOnly + access en memoria + silent-refresh + WS auth por primer mensaje | cookie/refresh/logout/WS con curl+cliente WS |
| **3** | `7216d1b` | `with_for_update`+`populate_existing` (doble gasto), Decimal, idempotencia Stripe (0003: `processed_stripe_events`+unique) | **test de concurrencia real**: 5 cargos → 3 OK + 2 rechazados |
| **4A** | `437a5fc` | enforcement de los 6 planes (max_members/courses/groups/rounds_history) + `/billing/plans`,`/users/me/plan` | límites en staging (socio 31→402, grupo 2→402) |
| **4B** | `949e737` | Stripe Checkout (`POST /billing/checkout`) + webhook `checkout.session.completed` + downgrade en cancelación + UI `/billing` | mocks: activación club/user, idempotente, params |
| **3B** | `2a7a12e` | Decimal en `balances.py` (largest-remainder) + guard suma-cero + `currency` en cuentas (0004) | suma-cero exacta ($30 pot → deltas [-1,+8,-7]) |

Rescate de drift: `9c5534e` — prod corría `balances.py` **+150 líneas NO commiteadas** (feature "breakdown");
se rescató al repo (un `rsync --delete` la habría borrado). Runbook de deploy: `2841ff5`.

## 3. Despliegue a producción
- **Deploy 1-4A** (`DEPLOY_PROD.md`): backup BD + snapshot código; rsync quirúrgico (sin `--delete`, excluye
  balances.py/compose/.env/creds); **cutover Alembic**: `alembic stamp 0001_baseline` → `upgrade head`
  (aplica 0002+0003); `.env` += `COOKIE_SECURE/SAMESITE/DOMAIN`; rebuild api + build `.next` + `up -d`.
  Verificado: 43 tablas, datos intactos (36 users/1 club/5 invoices), auth por cookie, /billing/plans.
- **Deploy 4B**: backend-only (sin migración), rsync + recreate api/frontend + `FRONTEND_URL` en `.env`.
- **Deploy 3B**: migración 0004 (`docker compose build migrate` + `run migrate alembic upgrade head`) + restart api.
- **Merge a `main`**: golf salía de `release/sprint2-cobranza` (arrastra COC) → se cherry-pickearon SOLO los
  commits golf (todos golf-only) a `main` vía worktree aislado, para NO mezclar con el portal COC.
- **Limpieza**: 11 archivos sueltos muertos de prod (`app/app/` anidado, `api/v1/config.py`, etc.) → cuarentena
  `/opt/golfbookvip/_quarantine_strays_*` (verificado 0 imports); `VERSION` corregido 1.15→1.29.0.

## 4. Incidente y fix — bucle de login (`047eded`)
Tras 2B, TODOS los usuarios quedaron sin poder loguear ("se queda iniciando sesión"): el middleware exigía la
cookie `gbv_refresh`, pero está scoped a `Path=/api/v1/auth` → invisible para las rutas del frontend → rebote a
login en bucle. **No se detectó** porque la verificación fue server-side + build; solo se ve en navegador real.
Hotfix: se quitó el gate del middleware (protección quedó en cliente+backend). **Gate SSR reintroducido bien**
(`e967baa`): cookie NO sensible `gbv_authed` con `Path=/` (visible), seteado en login/refresh y limpiado en
logout; **esta vez verificado con curl** (sin cookie→307, con cookie→200).

## 5. Smoke de Stripe (pagos reales test) — HECHO
- La key `rk_test_` **sí** crea Checkout Sessions.
- **Hallazgo:** el webhook de prod NO tenía `checkout.session.completed` habilitado → se agregó vía API
  (endpoint `we_1TMBOu...`, ahora 6 eventos). El otro endpoint es el de Odoo/COC (no se tocó).
- **Pago real de jugador** → Jugador Pro activado. **Pago real de club** → Club Starter activado (sub real
  `sub_1TooJt...`, eventos `evt_*` reales procesados idempotentes).
- **Enforcement demostrado**: club lleno a 100 socios → alta #101 por API real → **402 plan_limit** (upgrade_to
  club_pro). Suscripción de prueba cancelada en Stripe; todas las cuentas/club de prueba borradas → prod queda
  con solo datos reales (36 users/1 club/2 members).
- UI: link "Planes" al header del dashboard (`3c9c99a`) + mensaje "ya estás en el plan tope".

## Estado final
- **`main` == producción == Fases 1–4B + 3B** (migraciones 0001-0004). Repo golf limpio y **separado del COC**.
- Rollback disponible por deploy (`rollback_*.tgz` + backup BD + `alembic downgrade`).

## Pendientes / notas para la próxima
1. **Idempotencia de creación de booking (M1 quedó cubierto)** y **A1 (ledger firmado)** NO se hicieron:
   se dejó a propósito — `reconcile_account_balance` (Fase 3) ya reconstruye el saldo; reescribir el signo del
   `amount` histórico es riesgoso. Documentado en `FASE3B_SPEC.md`.
2. **Redis sigue muerto**: el WS de scoring es en-memoria (no escala multi-worker/instancia). Fase futura:
   pub/sub Redis si se necesita escalar el live scoring.
3. **Frontend**: 194 fetch ad-hoc (react-query instalado sin usar), i18n hardcodeado (184 ternarios), god
   components (rounds/[id]/page.tsx 4449 líneas). Deuda para escalar multi-cliente; no bloqueante.
4. **Smoke Stripe visual completo**: hecho con pagos reales test (jugador + club). Para producción real habría
   que pasar Stripe a modo LIVE con sus keys.
5. **`_quarantine_strays_*` en prod**: se puede borrar tras confirmar que nada se rompió (llevan >1h sin efecto).

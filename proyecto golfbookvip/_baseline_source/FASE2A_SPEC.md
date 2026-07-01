# FASE 2A — Endurecimiento de seguridad backend (autorización + reset-token + rate-limit)

> Contrato para Codex. El Arquitecto verifica en staging real (2 usuarios, rondas cruzadas).
> Solo backend. NO tocar frontend, dinero, ni migraciones. NO tocar producción.

## Contexto (hallazgos de auditoría a cerrar)
- **CR-2**: `POST /auth/forgot-password` DEVUELVE el reset token en el JSON → toma de cuenta total.
- **CR-3**: `POST /rounds/{round_id}/invite/{user_id}` (`rounds.py:389`, `invite_player`) NO verifica que
  el solicitante sea el creador → cualquiera se auto-inserta como jugador de cualquier ronda.
- **AL-1**: 4 GET de ronda SIN autenticación: `get_round` (~305), `bet-config` (~137), `skins` (~163),
  `scoreboard` (~980).
- **AL-2**: IDOR de lectura: `players` (~61) y `balances` (~1030) no verifican pertenencia a la ronda.
- **ME-1**: `GET /clubs/{club_id}/members` (`clubs.py:298`) no verifica membresía → volcado de padrón ajeno.
- **ME-6**: sin rate-limit en login/forgot-password (brute-force abierto).

## Hechos del código (ya verificados — respétalos)
- El modo espectador PÚBLICO es `GET /rounds/live/{invite_code}` y `/rounds/join/{invite_code}` (resuelven
  por `invite_code`, capability URL). **NO los toques, deben seguir públicos.**
- `RoundSpectator` NO tiene endpoints (tabla vestigial). El "viewer" legítimo de una ronda por `round_id`
  es: el creador (`Round.created_by`) o un `RoundPlayer` de esa ronda (o superadmin).
- `clubs.py` YA tiene helper `_require_club_role(db, club_id, user, min_role)` con jerarquía
  owner>admin>manager>staff y bypass de superadmin. `_get_club_role` devuelve el rol o None. Reúsalos.
- `app/services/mailer.py::send_email(to_email, subject, html_body, text_body=None)` es fire-and-forget
  seguro (retorna False si no hay SMTP, nunca lanza). Úsalo vía `BackgroundTasks`.
- `app/core/deps.py` expone `CurrentUser` y `DB`.

## Entregables

### 1. Reset de contraseña sin fuga (CR-2)
En `app/api/v1/auth.py::forgot_password`:
- NUNCA devuelvas el token ni reveles si el email existe. Responde SIEMPRE el mismo mensaje genérico
  (p.ej. `{"message": "Si el email está registrado, te enviamos un enlace de restablecimiento."}`) con 200,
  exista o no el usuario.
- Si el usuario existe: genera el token con `create_reset_token(...)` (ya existe) y ENVÍA el enlace por email
  vía `BackgroundTasks` + `mailer.send_email(...)`. El enlace es
  `https://golfbookvip.com/es/auth/reset-password?token=<token>`.
- Agrega `tpl_password_reset(user_name: str, reset_url: str) -> tuple[str, str]` en
  `app/services/email_templates.py` siguiendo el estilo de los `tpl_*` existentes (asunto + HTML branded).
- `forgot_password` debe aceptar `BackgroundTasks` como parámetro (hoy no lo tiene).
- NO cambies `reset_password` (ya valida el token correctamente).

### 2. Helpers de autorización de ronda + aplicarlos (CR-3, AL-1, AL-2)
En `app/api/v1/rounds.py`, crea dos helpers reutilizables cerca del inicio del archivo:
- `async def require_round_creator(db, round_id, user) -> Round`: 404 si la ronda no existe; 403 si
  `round_.created_by != user.id` y `not user.is_superadmin`; devuelve la ronda.
- `async def require_round_viewer(db, round_id, user) -> Round`: 404 si no existe; permite si el user es
  creador, superadmin, o existe un `RoundPlayer(round_id, user_id=user.id)`; si no, 403. Devuelve la ronda.

Aplica:
- `invite_player` (~389): al inicio, `await require_round_creator(db, round_id, current_user)` (necesita
  `CurrentUser`; hoy quizá no lo pide — agrégalo). Esta es la corrección CRÍTICA.
- `get_round` (~305), `get_bet_config` (~137), `get_skins` (~163), `scoreboard` (~980): agrega
  `current_user: CurrentUser` y `await require_round_viewer(...)` al inicio.
- `get_round_players` (~61), `get_balances` (~1030): agrega `require_round_viewer`.
- **NO toques** `live/{invite_code}` ni `join/{invite_code}`.
- Revisa el resto de endpoints de `rounds.py` que reciben `round_id` y MUTAN estado: si ya tienen el check
  inline `created_by == current_user.id`, déjalos (o cámbialos al helper si es trivial y sin riesgo). Si
  encuentras alguna otra mutación SIN check, ciérrala con `require_round_creator` y repórtalo.

### 3. IDOR de padrón de club (ME-1)
En `clubs.py` `GET /{club_id}/members` (~298): exige que `current_user` sea miembro o staff del club antes de
listar. Usa `_require_club_role(db, club_id, current_user, "staff")` si los miembros normales NO deben ver el
padrón completo, o una verificación de `ClubMember` si CUALQUIER miembro puede verlo. Elige "staff" (más
seguro) salvo que el patrón del resto de `clubs.py` indique lo contrario; documenta tu decisión.

### 4. Rate-limit en autenticación (ME-6)
- Agrega `slowapi` a `requirements.txt` y configúralo en `app/main.py` (Limiter por IP, exception handler).
- Aplica límites conservadores: `/auth/login` y `/auth/forgot-password` máx **5/minuto por IP**;
  `/auth/register` máx **10/minuto por IP**. No limites el resto.
- Debe degradar con gracia (si el storage no está, no romper el arranque). Usa storage en memoria por defecto.

## Fuera de alcance (NO lo hagas en 2A)
- JWT httpOnly cookie, refresh rotativo, protección de rutas en el middleware del frontend, token en WS.
  Eso es **Fase 2B** (cross-cutting FE+BE) y va aparte.

## Reglas
- Solo backend: `app/api/v1/auth.py`, `app/api/v1/rounds.py`, `app/api/v1/clubs.py`,
  `app/services/email_templates.py`, `app/main.py`, `requirements.txt`. No toques modelos, migraciones,
  frontend ni dinero.
- No inventes verificación de Docker (no lo tienes; el Arquitecto verifica en staging). Entrega: diffs
  resumidos por archivo, lista de endpoints de `rounds.py` que revisaste y su estado (protegido/ya-estaba),
  y la decisión del punto 3.

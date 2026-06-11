# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado [Semantic Versioning](https://semver.org/lang/es/).

Cada release está respaldada por un tag git (`git checkout v1.0.0-golfbookvip` para volver a ese estado).

---

## [1.27.0] - 2026-06-11

### Added — Tabla de posiciones del grupo (leaderboard)

Ranking competitivo de los miembros de un grupo sobre las rondas finalizadas del grupo:

- **Backend:** `GET /groups/{id}/leaderboard` (en `app/api/v1/groups.py`, respeta privacidad). Por cada ronda finalizada del grupo calcula el net total de cada jugador (net por hoyo con fallback a gross) y determina el ganador (menor net) entre quienes completaron la ronda. Devuelve a cada miembro con `rounds_played`, `wins`, `best_net`, ordenados por **victorias → handicap → mejor net** y con `position`.
- **Frontend:** nueva página `/groups/[id]/leaderboard` con tabla (medallas oro/plata/bronce al top 3, HCP, victorias, mejor net) + explicación; botón "Tabla de posiciones" en `/groups/[id]`.
- Funciona desde el día 1: sin rondas finalizadas ordena por handicap; con rondas, por victorias. Sin migración.

---

## [1.26.0] - 2026-06-11

### Added — Rondas de grupo (le da propósito a los grupos privados)

Los grupos privados ahora pueden tener rondas asociadas, conectando el `Round.group_id` que ya existía en el modelo pero no estaba cableado:

- **Backend:** `create_round` valida que el creador sea miembro activo del grupo cuando se manda `group_id` (403 si no). Nuevo endpoint `GET /groups/{id}/rounds` que lista las rondas del grupo (requiere membresía si es privado) con cancha, formato, estado, fecha y nº de jugadores.
- **Frontend `/groups/[id]`:** nueva sección "Rondas del grupo" con botón "Nueva ronda" → abre `/rounds/new?group_id=…&group_name=…`, lista de rondas con badge de estado (Programada/En juego/Finalizada) y enlace a cada una; empty state cuando no hay.
- **Frontend `/rounds/new`:** lee `?group_id=`/`?group_name=`, los manda al crear y muestra un banner "Ronda del grupo · <nombre>".
- Reutiliza el modelo y constraint existentes (`group_id` FK SET NULL). No requiere migración.

---

## [1.25.2] - 2026-06-10

### Changed — Tallas de equipo y grupos parejos en cupos no divisibles

El auto-armado y el armado manual ahora reparten parejo cuando el número de jugadores no es múltiplo del de equipos:

- **Grupos de salida parejos:** se forman `ceil(M/N)` grupos cuyos tamaños difieren a lo más en 1, repartiendo el HCP por snake. Ya no queda un grupo final chico (10 jug / 4 eq → grupos **4·3·3**, antes 4·4·2).
- **Tallas de equipo ≤1 + promedio de HCP parejo:** dentro de cada grupo, los equipos los toman los menos cargados (balancea tamaños) y se emparejan jugador↔equipo por HCP acumulado (el peor HCP al equipo más liviano), de modo que el **promedio** de handicap queda parejo entre equipos aunque difieran en 1 jugador.
- Se conserva la regla de **un jugador por equipo en cada grupo** (no junta compañeros). Reemplaza el snake-por-tier de 1.25.1 por `_balanced_assignment` en `app/api/v1/rounds.py`, usado por `POST /teams/generate` y `POST /auto-setup`.
- Validado con 40 000 cupos aleatorios (N=2..12, M=N..48): las invariantes (distinct por grupo, tallas equipo ≤1, tallas grupo ≤1) se cumplen siempre.
- Cambio **solo de backend** (rsync `rounds.py` + restart api).

---

## [1.25.1] - 2026-06-10

### Changed — Balanceo de equipos con snake draft

El armado de equipos por handicap ahora usa **snake draft (serpentina)** en vez del interleave por módulo (`idx % N`). El reparto alterna el orden de los equipos entre cada "tier" de handicap (tier 0 → 1..N, tier 1 → N..1, …), de modo que el equipo 1 ya no se queda con el mejor jugador de cada tier. Equilibra mucho mejor la fuerza de los equipos: en cupos divisibles (16/4, 12/3, 8/2) la suma de HCP por equipo queda **idéntica** (spread 0 vs 12/8/4 antes); en 20/4 baja de spread 15 a 3.

- Helper `_snake_team(idx, num_teams)` en `app/api/v1/rounds.py`. Aplicado en `POST /teams/generate` (manual) y `POST /auto-setup` (Gran Premio).
- En el auto-armado se **conserva la propiedad** de que cada grupo de salida (= un tier) tiene exactamente un jugador por equipo: dentro del tier la asignación sigue siendo una permutación de 1..N, solo cambia el orden. Verificado para 16/4, 20/4, 12/3, 8/2, 10/4.
- Cambio **solo de backend** (deploy: rsync `rounds.py` + restart api). El footer de la UI reflejará 1.25.1 hasta el próximo rebuild del frontend.

---

## [1.25.0] - 2026-06-10

### Added — Descarga de las guías en PDF desde /ayuda

Las guías de usuario (Jugador y Organizador, ES + EN) ahora se pueden **descargar en PDF** desde la página de Ayuda, además del acordeón existente.

- `docs/manual/build_pdf.py` (NUEVO) — genera los 4 PDFs desde los `.md` de `docs/manual/` con PyMuPDF (sin pandoc/weasyprint). Portada de marca, encabezado/pie por página, tablas/notas/listas estilizadas en verde GolfBookVIP. Regenerar: `python3 docs/manual/build_pdf.py`.
- `frontend/public/guides/*.pdf` (NUEVO) — los 4 PDFs servidos estáticamente: `GolfBookVIP-Guia-del-Jugador-ES.pdf`, `GolfBookVIP-Player-Guide-EN.pdf`, `GolfBookVIP-Guia-del-Organizador-ES.pdf`, `GolfBookVIP-Organizer-Guide-EN.pdf`.
- `frontend/src/app/[locale]/ayuda/page.tsx` → botón "Descargar guía en PDF" que abre el PDF correcto según la pestaña (Jugador/Organizador) y el idioma activo.

### Changed

- `version.ts` / `package.json` actualizados a 1.25.0 (venían rezagados en 1.23.0; el footer de la UI mostraba esa versión).

---

## [1.24.1] - 2026-06-05

### Fixed — El score por defecto (par) no se guardaba si no se tocaba

En la captura de score, el contador de cada jugador arranca en el **par del hoyo** con `dirty=false`. `submitScore` solo enviaba las filas tocadas con +/− (dirty), así que un hoyo dejado en el par **sin tocar nunca se guardaba** — el botón incluso se etiquetaba "Siguiente hoyo" y avanzaba dejando un hueco. Afectaba a **todas las modalidades** (la pantalla de captura y su guardado son comunes a stroke/match/florida/gran premio/skins; los formatos solo cambian las vistas de resultados).

- `frontend/src/app/[locale]/rounds/[id]/play/page.tsx` → `submitScore`: ahora, al guardar el hoyo, también persiste el valor mostrado (default = par) de cualquier jugador que aún no tenga score. Para filas de compañeros solo aplica si soy el capturista designado o el creador (en modo sin capturista cada quien guarda el suyo). No reenvía valores ya guardados, y el backend no marca conflicto al reenviar un valor idéntico.
- Botón: ahora muestra "Guardar hoyo" (verde) cuando hay algo por guardar — incluyendo defaults sin guardar — y "Siguiente hoyo" solo cuando todo el grupo ya tiene score.

---

## [1.24.0] - 2026-06-04

### Added — Modo Sol (alto contraste para leer en el campo)

El tema oscuro fotográfico de la app es difícil de leer bajo el sol directo en el campo. Se agrega un **botón flotante "Modo Sol" (☀️/🌙)** que activa un tema claro de alto contraste: fondo blanco (tapa las fotos de fondo), textos oscuros, tarjetas blancas y acentos (emerald/red/amber/blue/orange) oscurecidos para que sigan siendo legibles sobre blanco. Se prende/apaga a voluntad y se recuerda en `localStorage`; el diseño oscuro normal queda intacto para uso bajo techo.

Implementado como una capa de override CSS (`html[data-theme="sun"]`) en `globals.css` — sin tocar las ~50 pantallas una por una — más un script anti-flash `beforeInteractive` en el layout.

- `frontend/src/components/SunModeToggle.tsx` (NUEVO): botón flotante + persistencia.
- `frontend/src/app/globals.css`: overrides de Modo Sol (fondos, textos, bordes, acentos, inputs).
- `frontend/src/app/[locale]/layout.tsx`: script anti-flash + montaje del botón.

---

## [1.23.1] - 2026-06-04

### Fixed — Jugadores agregados manualmente no aparecían para capturar score

Al agregar un jugador desde la búsqueda (botón "Agregar"), quedaba con `status="invited"`. No existía ningún endpoint para pasar de "invited" a "confirmed", y toda la captura de score (`start_round`, `submit_score`, pantalla `/play`, finalización) filtra solo `confirmed`/`playing`. Resultado: solo el creador (confirmed al crear) y quien entraba por la liga (confirmed al unirse) aparecían para capturar; los agregados manualmente quedaban invisibles.

- `app/api/v1/rounds.py` → `invite_player`: ahora agregar manualmente confirma al jugador de una vez (`status="confirmed"` + `confirmed_at`), igual que el join por liga.

---

## [1.23.0] - 2026-05-29

### Added — Formato Medal Play por equipos con puntos por posición de grupo

Nuevo formato de torneo (estrenado en la ronda "Kike Jr. Birthday"): **Individual Medal Play** + equipos balanceados por handicap + puntos por posición **NET** dentro de cada grupo de salida. El equipo con más puntos es el **Campeón por Equipos**.

**Reglas de puntos por grupo:** 1.º = +2 · 2.º = +1 · último = −1 (siempre, sin importar el tamaño del grupo) · resto = 0. Empates resueltos por **tarjeta / countback** en net "según las ventajas" (últimos 9 → 6 → 3 hoyos → hoyo 18 → hoyo por hoyo; el net por hoyo ya incluye los strokes por stroke index).

- `app/services/team_points.py` (NUEVO): motor puro — `countback_key`, `points_for_position`, `rank_group`, `compute_team_points`.
- `GET /rounds/{round_id}/team-points` (público): grupos con posición/puntos por jugador, tabla de equipos, campeón y bandera de empate. Requiere `teams_published` + `tee_group` asignado; excluye retirados/observers.
- Frontend `/live/[code]`: sección "Campeón por Equipos" + desglose "Grupos de Salida"; oculta el marcador best-ball (hoyos ganados) cuando aplica este formato.

### Notes — Sincronización de trabajo previo desplegado

Este release también lleva al repo dos cambios que estaban en producción pero nunca se commitearon:

- **`max_handicap` por ronda** (tope de Course Handicap): `effective_handicap` en `scoring.py`, columna en `round.py`, schema y call-sites en `rounds.py`, páginas `rounds/[id]` y `rounds/new`.
- **Service Worker kill-switch v5** (`sw.js`): sin caché ni fetch handler — evita que un rebuild del frontend deje a usuarios PWA en "sin conexión".

---

## [1.22.0] - 2026-05-19

### Added — Bot conversacional Telegram (6 comandos de lectura)

v1.21 dejó el bot vinculable pero pasivo: solo recibía notificaciones del backend. v1.22 lo convierte en **conversacional**: el socio pregunta y el bot responde con datos reales desde la DB. Sin migración, sin frontend — toda la conversación es entre el socio y `@GolfBookVip_bot`.

**Comandos disponibles:**

| Comando | Qué hace |
|---|---|
| `/help` | Listado de comandos |
| `/saldo` | Balance en MemberAccount de cada club del socio |
| `/proxima` | Próxima reserva confirmada (cualquier club) |
| `/reservas` | Próximas 5 reservas confirmadas |
| `/handicap` | Hcp index actual + tendencia (último cambio) |
| `/cuenta` | Resumen: nombre, email, clubes activos |

Comandos no reconocidos → sugerencia de `/help`. Cuenta no vinculada (escribe al bot sin haber pasado por `/profile`) → mensaje guiando a vincular.

**Backend:**

- `app/services/telegram_handlers.py` (NUEVO) — 6 funciones `cmd_*` que reciben `(db, user)` ya autenticado y devuelven HTML compacto. Cada comando hace 1-2 queries sobre modelos existentes (`MemberAccount`, `Club`, `TeeTimeBooking`, `TeeTimeSlot`, `ClubMember`, `HandicapHistory`). Lectura solamente.
- `app/services/telegram.py` extendido con `set_my_commands()` helper y constante `BOT_COMMANDS`.
- `app/api/v1/telegram.py` webhook dispatcher refactorizado:
  - `/start` con token → flujo de vinculación (sin cambio)
  - `/start` sin token → equivalente a `/help` (si está vinculado) o invitación a vincular
  - Cualquier otro `/comando` → busca user por `chat_id`, dispatcher al handler
  - Comando inválido → `cmd_unknown` con sugerencia
  - Mensajes no-comando → ignorados silenciosamente

**Soporte de comandos con sufijo bot**: `/saldo@GolfBookVip_bot` se normaliza a `/saldo` (útil en grupos donde Telegram añade el sufijo).

### Setup post-deploy (Claude lo hizo)

Registrar los 6 comandos en BotFather (para autocompletado en clientes):

```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setMyCommands" \
  -H "Content-Type: application/json" \
  -d '{"commands":[...]}'
```

Verificable con `getMyCommands`.

### Notes

- **Solo lectura.** Crear/cancelar reservas desde el bot llega en v1.23 con inline keyboards.
- **Sin estados conversacionales**: cada comando es stateless, no hay flujos multi-step.
- **Multi-club**: `/saldo` y `/reservas` listan todos los clubes del socio; `/proxima` toma la más temprana de cualquier club.
- **Performance**: cada comando hace 1-3 queries pequeños; respuesta <500ms típicamente.
- **Sin nuevas dependencias**: reusa `httpx` (ya en deps) y los modelos existentes.

---

## [1.21.0] - 2026-05-19

### Added — Notificaciones por Telegram + UI de preferencias

v1.20 entregó email + in-app pero el canal "móvil instantáneo" estaba pendiente. Inicialmente se consideró WhatsApp via bot OpenClaw, pero **Telegram es técnicamente superior** (API oficial gratuita, sin dependencias intermediarias, sin costo por mensaje, bots no se bloquean). El bot `@GolfBookVip_bot` ya fue creado por el usuario en BotFather.

**Schema migration:**
```sql
ALTER TABLE users ADD COLUMN telegram_chat_id VARCHAR(50);
ALTER TABLE users ADD COLUMN telegram_username VARCHAR(100);
ALTER TABLE users ADD COLUMN notify_telegram BOOLEAN NOT NULL DEFAULT TRUE;
CREATE INDEX idx_users_telegram_chat ON users(telegram_chat_id) WHERE telegram_chat_id IS NOT NULL;
CREATE TABLE telegram_link_tokens (
  token VARCHAR(40) PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(), used_at TIMESTAMPTZ
);
CREATE INDEX idx_telegram_tokens_user ON telegram_link_tokens(user_id);
```

**Backend:**
- `app/core/config.py` — agregado `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME` (default `GolfBookVip_bot`), `TELEGRAM_WEBHOOK_SECRET`. Token vive solo en `.env` del servidor — nunca en repo.
- `app/models/telegram.py` (NUEVO) — `TelegramLinkToken` con token (PK), user_id (FK), created_at, used_at.
- `app/models/user.py` extendido — `telegram_chat_id`, `telegram_username`, `notify_telegram` (default True).
- `app/services/telegram.py` (NUEVO) — `send_telegram(chat_id, text)` async via `httpx` a `api.telegram.org/bot<TOKEN>/sendMessage` con parse_mode=HTML. Si token no configurado → warning + False (mismo patrón que mailer). También `get_me()` y `set_webhook()` helpers.
- `app/services/telegram_templates.py` (NUEVO) — 4 templates HTML compactos (3-8 líneas con emojis y formato Telegram): `tg_booking_confirmed`, `tg_booking_cancelled`, `tg_welcome_to_club`, `tg_tee_time_reminder`, más `tg_account_linked`, `tg_account_unlinked`, `tg_link_invalid` para el flujo de vinculación.
- `app/services/notifications.py` — `notify_user()` extendido con parámetro opcional `telegram_text`. Si `user.notify_telegram` + `user.telegram_chat_id` + `telegram_text` → agenda `send_telegram` via BackgroundTasks.
- `app/api/v1/users.py` — endpoints `POST /me/telegram/link-token` (genera token efímero 1h) y `DELETE /me/telegram` (desvincular). `UserOut` y `UserUpdate` extendidos con flags y campos de Telegram.
- `app/api/v1/telegram.py` (NUEVO) — `POST /telegram/webhook/{secret}` que recibe updates del bot, detecta `/start <token>`, valida el token, vincula `telegram_chat_id` con el user, responde con mensaje de confirmación.
- Triggers Telegram integrados en los **6 puntos** que ya tenían email/in-app: `book_tee_time`, `cancel_booking`, `join_club_by_invite_code`, `add_member_to_padron`, `import_padron`, `register` con club_code, y el cron de recordatorios.

**Frontend:**
- `/profile` — sección nueva "Notificaciones" con:
  - 3 toggles (in-app, email, Telegram)
  - Estado de vinculación de Telegram (badge "✅ Vinculado como @user" o "No vinculado")
  - Botón "Conectar mi Telegram" abre modal con instrucciones + deep link `https://t.me/GolfBookVip_bot?start=<token>`
  - Modal hace polling cada 3s a `/users/me` para detectar `telegram_chat_id` poblado y cerrarse automáticamente
  - Botón "Copiar link" como fallback
  - Botón "Desvincular Telegram" cuando está vinculado
- PATCH `/users/me` ahora acepta `notify_email`, `notify_inapp`, `notify_telegram` — se aplican on-change del toggle.

### Setup post-deploy (Claude lo hizo)

1. Token + secret agregados a `/opt/golfbookvip/.env` vía SSH (nunca commiteados)
2. Migración SQL aplicada en producción
3. Webhook registrado vía `setWebhook` → `https://api.golfbookvip.com/api/v1/telegram/webhook/<secret>`

### Notes

- **Telegram es opt-in**: por defecto `notify_telegram=True` pero sin `telegram_chat_id` no se envía nada. El socio debe vincular activamente.
- **El bot solo procesa `/start <token>` por ahora.** Bot conversacional (`/saldo`, `/proxima_reserva`, etc.) queda para v1.22+.
- **Tokens de vinculación expiran a 1h** y son single-use (se marcan `used_at` cuando se consumen).
- **WhatsApp queda definitivamente postergado.** Si en el futuro hay demanda específica, OpenClaw u otro proveedor se integra con el mismo patrón (helper + template + flag de user + parámetro opcional en notify_user).
- **El push notifications via Firebase** sigue pendiente (config existe desde v1.0, falta SW activo).

---

## [1.20.0] - 2026-05-19

### Added — Email sender real + notificaciones de Clubs SaaS

El módulo Clubs SaaS llevaba 10 releases sin emitir una sola notificación. Un socio podía ser agregado al padrón, recibir un cargo de $1500, ser cancelado de una reserva, y nunca enterarse. v1.20 cierra ese hueco: notificaciones in-app + email para los 4 eventos clave del módulo, y enciende el SMTP real (stub desde v1.0).

**Schema migration:**
```sql
ALTER TABLE users ADD COLUMN notify_email BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN notify_inapp BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE tee_time_bookings ADD COLUMN reminder_24h_sent BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE tee_time_bookings ADD COLUMN reminder_1h_sent BOOLEAN NOT NULL DEFAULT FALSE;
```

**Backend:**
- `app/services/mailer.py` (NUEVO) — `send_email(to, subject, html)` async usando `fastapi-mail` (ya en deps). Si MAIL_USERNAME/PASSWORD vacíos, log warning y retorna False sin romper. NUNCA lanza.
- `app/services/email_templates.py` (NUEVO) — 4 templates HTML inline ES:
  - `tpl_booking_confirmed` con desglose de jugadores y total cobrado
  - `tpl_booking_cancelled` con monto reembolsado
  - `tpl_welcome_to_club` con link al panel + invite_link copiable
  - `tpl_tee_time_reminder` para recordatorios 24h y 1h
- `app/services/notifications.py` extendido con `notify_user(db, user_id, type, title, body, data, email_subject, email_html, background_tasks)` — lee preferencias del user, crea in-app si `notify_inapp`, agenda email task si `notify_email`. Helper legacy `push()` se mantiene para compatibilidad.
- `app/core/config.py` — `MAIL_FROM` cambió default a `contacto@golfbookvip.com`. Agregado `MAIL_STARTTLS`, `MAIL_TIMEOUT`, `REMINDER_CRON_TOKEN`.
- Triggers integrados en `app/api/v1/clubs.py`:
  - `book_tee_time` → notifica `booking_confirmed` al booker + players con cuenta + sponsors
  - `cancel_booking` → notifica `booking_cancelled` al booker + payers
  - `join_club_by_invite_code` → `welcome_club`
  - `add_member_to_padron` → `welcome_club`
  - `import_padron` → `welcome_club` por cada socio creado/reactivado
- `app/api/v1/auth.py` — `register` con `club_code` también dispara `welcome_club`.
- `app/api/v1/admin.py` — endpoint `POST /admin/notifications/process-reminders` (auth via header `X-Reminder-Token` contra `settings.REMINDER_CRON_TOKEN`). Procesa ventanas 22-26h y 30min-1h30min, marca flags `reminder_*_sent`. Idempotente.

**Frontend:**
- `/notifications/page.tsx` — iconos + colores para los 4 tipos nuevos: `booking_confirmed` (Calendar emerald), `booking_cancelled` (CalendarX orange), `welcome_club` (Building2 emerald), `tee_time_reminder` (Bell amber).
- Bell counter sigue contando todos los unread (sin cambios).

### Changed

- `User.notify_email` y `User.notify_inapp` default `True` — sin UI todavía; opt-out manual via SQL o futura página `/profile`.
- `MAIL_FROM` ahora apunta a `contacto@golfbookvip.com` (cuenta del dominio que el usuario configurará).

### Notes

- **SMTP no se rompe sin configurar.** Si `MAIL_USERNAME` o `MAIL_PASSWORD` están vacíos en `.env`, los envíos hacen log de warning y siguen — los bookings y otros endpoints funcionan normal con solo in-app.
- **Recordatorios** requieren un cron externo que llame al endpoint cada N minutos con el header de token. Ejemplo: `*/15 * * * * curl -X POST -H "X-Reminder-Token: $TOKEN" https://api.golfbookvip.com/api/v1/admin/notifications/process-reminders`. Si `REMINDER_CRON_TOKEN` está vacío en `.env`, el endpoint queda inaccesible (safe-by-default).
- **WhatsApp via OpenClaw** queda para v1.21 — necesita definir el contrato del bot.
- **UI de preferencias** en `/profile` queda para v1.21+.
- **Templates externos / locale-aware** (Jinja2 + `User.preferred_locale`) para v1.21+.

---

## [1.19.0] - 2026-05-19

### Added — Wizard de creación de club + Import CSV de padrón

Crear un club en producción dejaba al admin con un esqueleto vacío y 4 pantallas distintas por recorrer (tipos, settings, padrón uno por uno). Esta release entrega un club operativo en un solo flujo, y resuelve el TODO de "Import CSV del padrón" que llevaba 7 releases como placeholder.

**Backend (`app/api/v1/`):**
- `POST /clubs/{club_id}/padron/import` (NUEVO en `clubs.py`):
  - Acepta hasta 500 rows con `email` (requerido), `member_number`, `membership_type_id` o `membership_type_name` (lookup case-insensitive), `joined_at`, `expires_at`, `notes`
  - Vincula a `users` existentes por email; los no encontrados se reportan en `not_found` con `row_index`
  - Reactiva ClubMembers inactivos en lugar de duplicar
  - Detecta duplicados dentro del mismo CSV (mismo email en 2 filas → la 2ª en `errors`)
  - Marca cada fila con `onboarding_source='manual_import'`
  - Response incluye contadores + listas detalladas + `invite_link` del club para compartir con los pendientes
- `POST /users/lookup-batch` (NUEVO en `users.py`):
  - Recibe `{emails: [str]}` máx 500, retorna `{matches: [...], not_found: [...]}`
  - Sin club_id en la ruta — usado por el wizard para validar antes de crear el club

**Frontend:**
- `/admin/clubs/new` (NUEVO) — wizard de 4 pasos con stepper visual:
  1. **Datos básicos** del club + selector de plan
  2. **Tipos de membresía** (lista dinámica; opcional)
  3. **Padrón** (componente `CsvPadronImport`; opcional, saltable)
  4. **Review + Crear** con log de operaciones en vivo
  - Submit ejecuta secuencialmente: POST club → POST tipos → POST padron/import. Si un paso intermedio falla, continúa con los demás y reporta al final.
- `components/clubs/CsvPadronImport.tsx` (NUEVO) — componente reutilizable:
  - Drag & drop / file input para CSV
  - Plantilla descargable con headers ES (`email,member_number,membership_type,joined_at,expires_at,notes`)
  - Aliasing de headers en español + inglés (`correo`/`email`, `tipo`/`membership_type`, etc.)
  - Preview con ✓/⚠️ por fila tras validate (max 200 visibles, scroll)
  - Dos modos: standalone (importa directo con `clubId`) y wizard (expone rows validadas via `onRowsReady`)
  - Tras import: banner con resumen + link copiable para los emails pendientes
- `/admin/clubs/page.tsx` — botón "Nuevo" ahora redirige al wizard; modal inline eliminado (~85 líneas menos)
- `/club/{id}/members/page.tsx` — tab nueva "Importar CSV" en el modal de Agregar socio (3 tabs total: Invitar / Buscar / CSV)
- `/club/{id}/page.tsx` — eliminada la entrada "Import CSV del padrón — Coming soon" del placeholder de próximas features

**Dependencia nueva:** `papaparse` ^5.5.3 + `@types/papaparse` (parsing robusto de CSV con quoted fields, BOM, multi-line escapes).

### Changed

- `ClubMember.onboarding_source` ahora acepta el valor `'manual_import'` (sin cambio de schema; la columna es VARCHAR(20) sin CHECK constraint)
- El modal inline de "Nuevo club" en `/admin/clubs` se eliminó; el botón redirige al wizard

### Notes

- **CSV solo vincula `users` existentes.** No se crea cuenta automática (sin SMTP; pendiente desde v1.0). Los emails sin cuenta se devuelven con el link de invitación a compartir.
- `max_length=500` por import para evitar timeouts en clubes grandes. Si tienes más de 500 socios, divide el CSV en lotes.
- Los tipos de membresía del CSV se matchean por nombre case-insensitive contra los tipos activos del club; sin match → queda NULL (admin asigna después).

---

## [1.18.0] - 2026-05-19

### Added — Auto-cobro de green fees con refund automático al cancelar

Cierra el ciclo del booking que arrancó en v1.17: cuando un socio confirma una reserva con `fee_amount > 0` en cualquier `tee_time_booking_player`, ahora se generan `AccountTransaction(type='green_fee')` automáticamente en las cuentas correspondientes. Al cancelar el booking, se emiten refunds simétricos. Sin cambios obligatorios de UI — la página de detalle de cuenta ya mostraba todos los tipos.

**Reglas de pago:**
- `player_type='member'` → cargo a cuenta del propio socio
- `player_type='guest'`:
  - si `Club.guest_fee_to_sponsor=true` → cargo al sponsor
  - si false + guest tiene user_id → cargo al guest
  - sin user_id ni sponsor → SKIP (cash en sitio, queda solo `fee_amount` en la fila del player)
- `player_type='public'` → cargo a cuenta propia si tiene user_id, else SKIP

**Saldo negativo permitido** para auto-posteo de green fees. Un socio con `credit_limit=0` y `balance=0` puede reservar igual; el cargo queda como deuda. El club cobra en su flujo normal de pagos.

**Backend (`app/api/v1/clubs.py`):**
- `_apply_transaction` (existente) ahora acepta `enforce_credit_limit: bool = True`. Sigue siendo el default para charges manuales; v1.18 lo pasa en `False` para auto-cobro de green fees.
- `_post_booking_fees(db, booking, slot, club, current_user)` (NUEVO) — itera `tee_time_booking_players`, calcula payer según reglas, 1 transaction por player con `reference_id=player.id` y `reference_type='tee_time_booking_player'`. Acumula totales y devuelve dict para el response.
- `_refund_booking_fees(db, booking, current_user)` (NUEVO) — busca transactions de green_fee del booking, emite refund por cada una. Idempotente: skip si ya existe refund para ese player_id (prevención de doble-cancel).
- `book_tee_time` ahora llama a `_post_booking_fees` al final y añade `total_charged` + `charges_count` al response.
- `cancel_booking` ahora llama a `_refund_booking_fees` antes del status update y añade `refunded_total` + `refund_count` al response.
- `GET /clubs/{id}/tee-times/bookings/{booking_id}/transactions` (NUEVO) — lista AccountTransaction asociadas al booking (charges + refunds). Permisos: booker o staff.

**Frontend (`/club/[id]/tee-times`):**
- Toast emerald arriba del listado de slots: tras booking exitoso muestra `"Reserva confirmada · $XXX cobrados (N cargos)"`. Tras cancel: `"Reserva cancelada · $XXX reembolsados"`. Botón X para cerrar manualmente. No bloqueante.
- Nota del sidebar de fees actualizada: `"Los green fees se cobrarán automáticamente a la cuenta del responsable al confirmar la reserva. Cancelar genera un reembolso automático."` (antes decía "v1.18 (no se cobran aún)").

### Notes

- **No backfill**: bookings creados antes de v1.18 no reciben transactions retroactivas. Si se cancela uno viejo, el refund encuentra 0 charges y simplemente marca cancelled sin reembolsar.
- **Cash players** (public sin user_id, guest sin sponsor con guest_fee_to_sponsor=false): el `fee_amount` queda en la fila del player como referencia, sin transaction. El club cobra en sitio. Reporte agregado de cash queda para v1.19+.
- **Tracking visitas anuales por guest_email**: pendiente. `max_guest_visits_per_year` sigue siendo informativo.
- **Notificaciones email/WA**: pendiente para v1.20.

---

## [1.17.0] - 2026-05-19

### Added — Booking multi-jugador con guests nombrados + enforcement del híbrido

Hoy el booking solo guardaba un contador (`players_count`); v1.17 introduce un detalle por jugador con tipo (member / guest / public), sponsor nombrado, fee calculado por tier, y enciende todas las reglas duras del híbrido que llevaban un mes en producción como cosméticas.

**Schema nuevo (`tee_time_booking_players`):**
- `id` UUID PK, `booking_id` UUID FK CASCADE
- `player_type` VARCHAR(20) CHECK (member | guest | public)
- `user_id` UUID FK users (nullable — guests/public sin cuenta usan guest_name)
- `guest_name` VARCHAR(200), `guest_email` VARCHAR(255)
- `sponsor_id` UUID FK users (guest con sponsor)
- `fee_amount` NUMERIC(10,2) — calculado al reservar según slot.tier + player_type (cobro real llega en v1.18)
- `added_by` UUID FK users, `created_at` TIMESTAMPTZ
- Índices en booking_id, user_id (partial), sponsor_id (partial)
- Backfill: 1 fila placeholder `member` por booking existente

**Backend (`app/api/v1/clubs.py`):**
- `POST /clubs/{id}/tee-times/{slot_id}/book` REFACTOR — acepta `players[]` con detalle. Schemas nuevos: `BookingPlayerIn`, `BookingCreate` ahora con `players: list[BookingPlayerIn]`.
- `GET /clubs/{id}/tee-times/bookings/{booking_id}` (NUEVO) — detalle de booking con players resueltos (booker o staff).
- `GET /clubs/{id}/tee-times` AMPLIADO — cada booking incluye `players[]` con nombres resueltos y `total_fees`. Retrocompat: mantiene `user_name`, `players_count`.
- Helpers nuevos: `_calculate_fee(slot, player_type)`, `_validate_booking(club, slot, players, booker_id, db)` (raises 422 con lista de errores), `_resolve_players_for_booking(db, booking_id)`.

**Enforcement encendido (eran "dead config" desde v1.14/v1.15):**
- `Club.allow_guests=false` → rechaza guest/public
- `Club.guest_requires_sponsor=true` + guests → cada guest requiere `sponsor_id` válido (socio activo del club)
- `Club.max_guests_per_booking` → límite duro al conteo de guests
- `Slot.tier='members_only'` → rechaza `player_type='public'`
- `Slot.tier='members_priority'` + public → solo dentro de `Club.public_advance_days`
- `Club.access_type='private'` → rechaza public en cualquier slot
- `Club.members_advance_days` → ventana máxima para socios
- Member validation: si `player_type='member'`, el user_id debe ser ClubMember activo
- Errores se acumulan y retornan en `detail: list[str]` con HTTP 422

**Frontend (`/club/[id]/tee-times`):**
- Modal de Reserva rediseñado, max-w-2xl con lista vertical de jugadores
- Cada fila: dropdown tipo (Socio / Invitado / Público), inputs dinámicos según tipo
  - Socio → dropdown del padrón completo, excluye los ya tomados en otras filas, muestra HCP y member_number
  - Invitado → nombre + email (opcional) + dropdown sponsor (requerido si `guest_requires_sponsor`)
  - Público → nombre + email (deshabilitado si tier='members_only' o allow_guests=false)
- Botón "+ Agregar jugador" hasta `slot.max_players`
- Fee inline por fila + sidebar de total (calc cliente, recalc backend)
- Banner rojo con bullets cuando backend retorna 422 con lista de errores
- Slot card ahora muestra jugadores nombrados de cada booking con tipo y sponsor
- Lazy load del padrón + settings del club al abrir el modal
- Lee `currentUserId` desde `/users/me` para preseleccionarse como primera fila

### Schema migration

```sql
CREATE TABLE tee_time_booking_players (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  booking_id UUID NOT NULL REFERENCES tee_time_bookings(id) ON DELETE CASCADE,
  player_type VARCHAR(20) NOT NULL CHECK (player_type IN ('member','guest','public')),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  guest_name VARCHAR(200), guest_email VARCHAR(255),
  sponsor_id UUID REFERENCES users(id) ON DELETE SET NULL,
  fee_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
  added_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_booking_players_booking ON tee_time_booking_players(booking_id);
CREATE INDEX idx_booking_players_user ON tee_time_booking_players(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_booking_players_sponsor ON tee_time_booking_players(sponsor_id) WHERE sponsor_id IS NOT NULL;
-- Backfill placeholder member para bookings existentes
INSERT INTO tee_time_booking_players (booking_id, player_type, user_id, fee_amount, added_by)
SELECT b.id, 'member', b.user_id, 0, b.user_id FROM tee_time_bookings b
WHERE NOT EXISTS (SELECT 1 FROM tee_time_booking_players p WHERE p.booking_id = b.id);
```

### Notes

- **v1.18 pendiente:** cobro real con `_apply_transaction` usando `fee_amount` ya persistido. Member → cargo a cuenta propia. Guest → cargo al sponsor si `guest_fee_to_sponsor=true`, else a cuenta del guest si tiene una.
- `max_guest_visits_per_year` sigue siendo informativo (requiere tracking por email; queda para v1.18+).
- Notificaciones email/WA al confirmar booking — pendiente para v1.20.

---

## [1.16.0] - 2026-05-19

### Added — Auto-onboarding de socios al club + búsqueda manual

El club deja de capturar el padrón a mano. Ahora comparte un link/QR único y los socios se auto-registran y quedan vinculados al instante. El admin solo ajusta excepciones (tipo de membresía, número de socio, vencimiento). Cobertura completa de 5 escenarios: usuario nuevo, usuario existente sin sesión, con sesión, ya socio (idempotente) y búsqueda manual del admin.

**Schema migration:**
- `clubs`: + `invite_code VARCHAR(32) UNIQUE`, + `default_membership_type_id INTEGER REFERENCES membership_types(id) ON DELETE SET NULL`
- `club_members`: + `onboarding_source VARCHAR(20) DEFAULT 'manual'` (valores: `manual` | `invite_link` | `self_join`)
- Clubes existentes recibieron código auto-generado tipo `SAUCITO-12A5`.

**Backend nuevos:**
- `GET /clubs/by-code/{invite_code}` (PÚBLICO, sin auth) → resuelve el código a info del club (id, nombre, logo, ciudad, conteo de socios). Sirve a la landing `/join-club/{code}`.
- `POST /clubs/by-code/join` (auth) → vincula al usuario actual al club. **Idempotente:** si ya es socio retorna `already_member: true`. Usa `default_membership_type_id` del club si está configurado. `onboarding_source='self_join'`.
- `POST /clubs/{id}/invite-code/rotate` (admin) → genera nuevo código; el viejo deja de funcionar inmediatamente.
- `GET /clubs/{id}/users/search?q=...` (manager) → autocomplete sobre `users` excluyendo los que ya son socios activos. Mínimo 3 chars; máx 50 resultados.

**Backend modificados:**
- `POST /auth/register` ahora acepta `club_code` opcional. Si presente y válido, crea `ClubMember` en la misma transacción con `onboarding_source='invite_link'`. Si inválido, registra al usuario normalmente sin fallar. Response añade `joined_club_id` y `joined_club_name`.
- `POST /clubs` (create_club) genera un `invite_code` único al crear el club; añade `onboarding_source='manual'` al socio fundador.
- `GET/PATCH /clubs/{id}/settings` extendido con `invite_code` (read-only) y `default_membership_type_id` (read+write, valida que el tipo pertenezca al club).

**Frontend nuevo:**
- `/join-club/{code}` — landing pública con info del club, 3 estados de CTA:
  - Sin sesión: "Registrarme y unirme" / "Ya tengo cuenta — Entrar"
  - Con sesión, no socio: botón "Unirme al club"
  - Ya socio: mensaje + redirect al panel
- Convive con el `/join/{code}` existente (invitaciones a rondas) sin colisión de rutas.

**Frontend modificado:**
- `/auth/register` lee `?club_code=` del query, lo envía al backend, y si el response trae `joined_club_id` redirige a `/club/{id}`.
- `/auth/login` lee `?club_code=`, después de login hace `POST /clubs/by-code/join` y redirige al panel del club. Banner contextual visible.
- `/club/[id]/members` — botón "Agregar" abre modal con 2 tabs:
  - **Compartir invitación** (default): código grande, link copiable, QR descargable (SVG), nota explicativa para el admin
  - **Buscar usuario**: form existente por email/username sobre `/padron`
- `/club/[id]/settings` — nueva sección "Invitación de socios" arriba con código, link, QR, botón "Rotar código" (rojo + confirm), y selector "Tipo de membresía por defecto".

### Reglas de producto

- `ClubMember.user_id` se mantiene NOT NULL. Sólo registra socios con cuenta de app. (Captura de personas sin cuenta queda fuera de scope — futuro: invitaciones por email.)
- Un usuario puede ser socio de varios clubes simultáneamente.
- Al auto-unirse: `status='active'` (sin aprobación manual del admin), `joined_at=hoy`, `membership_type_id=club.default_membership_type_id` (puede ser NULL).
- Idempotencia garantizada por `UniqueConstraint(club_id, user_id)` + chequeo en endpoint.
- Rotación del código es destructiva sólo para el código (no afecta socios ya registrados).

### Notes

- v1.17.0 retoma el booking multi-jugador con guests nombrados (pospuesto desde v1.16.0 para priorizar el onboarding).
- El QR se exporta como SVG. Conversión a PNG queda al cliente (open en navegador → screenshot, o usar herramienta externa).

---

## [1.15.0] - 2026-05-15

### Added — Clubs SaaS Fase 4.2 · Tiers y pricing en tee_time_slots

Segunda de 4 sub-releases del híbrido. Cada slot ahora tiene tier de acceso y 3 tarifas (socio/invitado/público).

**Schema migration (`tee_time_slots`):**
- `tier VARCHAR(20) NOT NULL DEFAULT 'members_only'` con CHECK `IN ('members_only','members_priority','public')`
- `green_fee_member NUMERIC(10,2) NOT NULL DEFAULT 0`
- `green_fee_guest NUMERIC(10,2) NOT NULL DEFAULT 0`
- `green_fee_public NUMERIC(10,2) NOT NULL DEFAULT 0`

Slots existentes quedan en `members_only` con tarifas 0 (retrocompatible).

**Backend:**
- `GET /clubs/{id}/tee-times` ahora devuelve `tier`, `green_fee_member`, `green_fee_guest`, `green_fee_public` por slot.
- `POST /clubs/{id}/tee-times` y `POST /tee-times/generate` aceptan los 4 campos nuevos. Validan `tier in VALID_TIERS`.
- `PATCH /clubs/{id}/tee-times/{slot_id}` extendido para editar tier/precios.
- `PATCH /clubs/{id}/tee-times/bulk` — **endpoint nuevo** para aplicar cambios masivos a un rango (fechas + opcionalmente horas/weekdays): permite "ponle precio member=500/public=1500 a todos los slots de viernes-domingo de junio".

**Frontend (`/club/{id}/tee-times`):**
- Cada slot muestra **badge de tier** (rojo "Solo socios" / ámbar "Prioridad socios" / verde "Público") + **mini-pricing inline** ("S $500  I $1000  P $1500" con colores).
- Modal **"Generar slots"** extendido con sección Tier + 3 inputs de precio.
- Modal **"Crear slot individual"** extendido idem.
- Los precios solo aparecen en la tarjeta si alguno > 0 (clubes privados puros pueden no usar precios).

### Notes

- Los precios todavía no se cobran automáticamente en booking. Eso llega en v1.17.0.
- v1.16.0 agrega booking multi-jugador con guests nombrados y reglas de sponsor.
- Endpoint bulk usa parámetros granulares: `time_start`/`time_end` (rango horario), `weekdays` (array 0-6) para reglas tipo "fin de semana antes de 10am es members_only".

---

## [1.14.0] - 2026-05-15

### Added — Clubs SaaS Fase 4.1 · Configuración del club (acceso híbrido)

Primera de 4 sub-releases para soportar clubes híbridos (socios + público). Esta versión agrega la **configuración**; las siguientes integran las reglas en bookings/pricing/cobro.

**Schema migration aplicada en producción (`clubs`):**
- `access_type VARCHAR(20) NOT NULL DEFAULT 'private'` con CHECK `IN ('private','semi_private','public')`
- `allow_guests BOOLEAN NOT NULL DEFAULT TRUE`
- `guest_requires_sponsor BOOLEAN NOT NULL DEFAULT TRUE`
- `max_guests_per_booking INT NOT NULL DEFAULT 3`
- `max_guest_visits_per_year INT NOT NULL DEFAULT 6`
- `guest_fee_to_sponsor BOOLEAN NOT NULL DEFAULT TRUE`
- `members_advance_days INT NOT NULL DEFAULT 30`
- `public_advance_days INT NOT NULL DEFAULT 7`

Todos los clubes existentes quedan con defaults sensatos (privado puro), retrocompatible.

**Backend:**
- `GET /clubs/{id}/settings` — config completa (requiere staff)
- `PATCH /clubs/{id}/settings` — actualizar parámetros uno o varios (requiere admin+)
- `GET /clubs/{id}/dashboard` ahora incluye `access_type` para que el panel muestre el badge.

**Frontend — `/[locale]/club/{id}/settings`:**
- Sección 1 **Tipo de acceso**: 3 tarjetas grandes (Privado / Híbrido / Público) con icono, color y descripción. Click para cambiar (solo Owner/Admin).
- Sección 2 **Política de invitados**: 3 toggles (allow_guests, guest_requires_sponsor, guest_fee_to_sponsor) + 2 campos numéricos (max_guests_per_booking, max_guest_visits_per_year). Auto-disable de campos dependientes cuando se desactiva el padre.
- Sección 3 **Ventanas de reserva**: 2 campos numéricos (members_advance_days, public_advance_days). public_advance_days se deshabilita si access_type=private.
- Auto-save al cambiar cualquier campo + flash "✓ Guardado" en header.
- Vista de solo-lectura para Manager/Staff (warning visible).

**Frontend — panel `/club/{id}`:**
- Nueva tarjeta gris "Configuración del club" (full-width abajo) con badge del tipo de acceso (rojo Privado / ámbar Híbrido / verde Público).

### Notes

- Esta versión **NO impone las reglas en los endpoints de booking todavía**. Lo hará v1.15.0+ cuando integremos tiers en slots.
- Roadmap restante para híbrido completo:
  - v1.15.0 — Tiers y pricing en tee_time_slots (members_only/members_priority/public + green_fee_member/guest/public)
  - v1.16.0 — Booking multi-jugador con guests nombrados + validación de sponsor + limit checks
  - v1.17.0 — Cobro automático: al confirmar booking, generar transacciones charge en cuentas correctas

### Roadmap pendiente Clubs SaaS

| Versión | Tema |
|---|---|
| v1.15.0 | Tiers y pricing en slots |
| v1.16.0 | Booking con guests nombrados |
| v1.17.0 | Cobro automático de green fees |
| v1.18.0 | Onboarding wizard nuevo club |
| Backlog | Import CSV padrón, notificaciones, dominio personalizado, fix BuildKit |

---

## [1.13.0] - 2026-05-15

### Added — Clubs SaaS Fase 3 · Estado de cuenta de socios

Sistema de cuentas del miembro con cargos, pagos, ajustes y balance en tiempo real. Permite al club facturar consumos y rastrear deuda/crédito.

**Backend (`/api/v1/clubs/{id}/accounts/*`):**
- `GET /accounts` — lista resumen de cuentas del club con totales (filtros `only_debtors`, `q`). Requiere staff.
- `GET /accounts/{user_id}` — detalle de cuenta (balance, límite, info del miembro). Accesible por el propio user, staff o súper-admin.
- `GET /accounts/{user_id}/transactions` — historial con filtros `date_from`, `date_to`, `type_filter`, `limit`. Mismo scoping.
- `POST /accounts/{user_id}/charge` — registrar cargo (manager+). Tipos: `charge`, `membership_fee`, `green_fee`, `bet_loss`.
- `POST /accounts/{user_id}/payment` — registrar pago (manager+). Método: `cash`, `card`, `transfer`, `other`.
- `POST /accounts/{user_id}/adjust` — ajuste manual con monto firmado y motivo (admin+).
- `PATCH /accounts/{user_id}/credit-limit` — cambiar límite de crédito (admin+).
- `GET /my-account` — atajo del socio para ver su balance.

**Convención del balance:**
- `balance > 0` → saldo a favor del socio (crédito)
- `balance < 0` → deuda del socio con el club
- Cargos restan, pagos suman. Ajustes manuales usan signo explícito.
- `credit_limit` define el saldo negativo máximo permitido (default 0 = sin deuda).

**Auditoría:** cada transacción guarda `balance_after` (snapshot del saldo) + `created_by` (qué staff la registró). Las transacciones nunca se eliminan — solo se crean ajustes inversos.

**Frontend — páginas nuevas:**
- `/[locale]/club/{id}/accounts` — lista de cuentas con 3 tarjetas resumen (deuda total / crédito total / # de cuentas), filtro "solo deudores", búsqueda, tabla clicable.
- `/[locale]/club/{id}/accounts/{user_id}` — detalle:
  - Hero con avatar, balance grande coloreado (rojo deuda, verde crédito), límite editable
  - 3 botones de acción: **Pago** (verde), **Cargo** (rojo), **Ajuste** (azul, solo admin+)
  - Tabla cronológica de movimientos con tipo coloreado, concepto, monto firmado y saldo después
  - Botón "Imprimir" con CSS print-friendly (header oculto, fondos blancos, texto oscuro)

**Frontend — integración:**
- Panel del cliente (`/club/{id}`): nueva tarjeta verde "Estado de cuenta" + grid reorganizado (4 tarjetas activas: Padrón / Tipos / Tee times / Cuenta)
- Padrón (`/members`): nuevo icono `$` por miembro → atajo directo a su estado de cuenta

**Matriz de permisos:**

| Acción | Owner | Admin | Manager | Staff | Miembro (propio) |
|---|---|---|---|---|---|
| Ver lista cuentas | ✓ | ✓ | ✓ | ✓ | — |
| Ver cuenta de un socio | ✓ | ✓ | ✓ | ✓ | ✓ |
| Registrar cargos | ✓ | ✓ | ✓ | — | — |
| Registrar pagos | ✓ | ✓ | ✓ | — | — |
| Ajuste manual | ✓ | ✓ | — | — | — |
| Cambiar límite crédito | ✓ | ✓ | — | — | — |

### Notes

- PDF exportable: usa el navegador (Ctrl+P) → save as PDF. Mejor render con generación server-side queda para v1.13.x.
- Generación masiva de cuotas mensuales (ej. cobrar 100 cuotas el día 1 del mes) pendiente.
- Recibos por email/WhatsApp al registrar pago pendientes.
- Integración con el sistema de tee times (cobrar green fee automático al jugar) pendiente.

---

## [1.12.0] - 2026-05-15

### Added — Clubs SaaS Fase 2 · Tee times (reservas de salidas)

Sistema básico de reservas de tee times integrado con el panel del cliente. Los socios reservan, el admin gestiona el calendario.

**Schema migration aplicada en producción:**
- `tee_time_slots`: agregada columna `club_id UUID REFERENCES clubs(id) ON DELETE CASCADE` + índice `(club_id, date)` + unique key reemplazada por `(club_id, date, time)`.
- `tee_time_slots.course_id` ahora nullable (era required) para hacer el slot pertenezca al club, no al course físico.

**Backend (`/api/v1/clubs/{id}/tee-times/*`):**
- `GET /tee-times?date_from&date_to` — lista slots del rango (default: hoy + 14 días) con sus bookings. Accesible por staff o miembros activos.
- `POST /tee-times/generate` — generación masiva (admin+): rango de fechas, hora inicio/fin, intervalo en minutos (2-60), max_players (1-8), opcionalmente filtro por días de la semana. Máximo 90 días por llamada. Duplicados se omiten silenciosamente.
- `POST /tee-times` — crear slot individual (admin+).
- `PATCH /tee-times/{slot_id}` — editar max_players o bloquear/desbloquear con razón (admin+).
- `DELETE /tee-times/{slot_id}` — eliminar slot (admin+, rechaza si hay reservas activas, 409).
- `POST /tee-times/{slot_id}/book` — reservar. Miembros activos del padrón o staff pueden reservar. Staff puede reservar a nombre de otro user. Confirmación inmediata (sin workflow de aprobación en MVP). Valida disponibilidad atomically.
- `DELETE /tee-times/bookings/{booking_id}` — cancelar reserva. Dueño de la reserva o manager+.
- `GET /tee-times/my-bookings` — mis reservas (próximas por default).

**Frontend — página `/[locale]/club/{id}/tee-times`:**
- Navegación por día con botones ←/→ y selector de fecha + botón "Hoy"
- Grid de slots con barra de ocupación (verde<50%, ámbar<100%, naranja=lleno), estado visible (bloqueado/lleno/disponible)
- Lista de socios reservados por slot con nombre y # de jugadores
- Acciones admin: bloquear/desbloquear (con razón opcional), eliminar slot, generar slots en bulk
- Modal "Generar slots" con preview de qué se va a crear (rango de fechas, hora, intervalo, cupo)
- Modal "Reservar" para socios: # de jugadores, notas, confirma con animación
- Cancelación de reserva con confirm dialog

**Panel del cliente (`/[locale]/club/{id}`):**
- Nueva tarjeta ámbar "Tee times" full-width abajo de Padrón/Tipos
- "Próximamente" actualizado: queda Estado de cuenta, Empleados, Import CSV, Notificaciones de reserva

**Matriz de permisos (extendida con tee times):**

| Acción | Owner | Admin | Manager | Staff | Miembro | Súper-admin |
|---|---|---|---|---|---|---|
| Ver calendario | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Generar/crear slots | ✓ | ✓ | — | — | — | ✓ |
| Bloquear/eliminar slot | ✓ | ✓ | — | — | — | ✓ |
| Reservar para sí | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Reservar para otro | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| Cancelar reserva propia | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Cancelar reserva ajena | ✓ | ✓ | ✓ | — | — | ✓ |

### Notes

- Confirmación de reservas es inmediata (status `confirmed`) en MVP. Workflow de aprobación pendiente para Fase 2.1.
- Límites por miembro (ej. máx 1 reserva por día) no implementados todavía. Pendiente Fase 2.1.
- Notificaciones por email/WhatsApp al reservar/cancelar pendientes.
- Import CSV de padrón sigue pendiente para Fase 1.5.

---

## [1.11.0] - 2026-05-15

### Added — Clubs SaaS Fase 1 · Padrón de miembros + Tipos de membresía

Primera versión funcional para que el cliente-admin del club gestione su operación. Cierra el ciclo: del setup (v1.10) al **uso diario** (v1.11).

**Backend — matriz de permisos por rol (`/api/v1/clubs/*`):**
- Helper `_require_club_role(club_id, user, min_role)` con jerarquía owner > admin > manager > staff. Súper-admin bypass automático.
- `GET /clubs/{id}/my-role` — devuelve `role`, `is_superadmin`, `can_manage_members`, `can_manage_membership_types`, `can_manage_staff`.

**Backend — CRUD de tipos de membresía (Owner/Admin):**
- `GET /clubs/{id}/membership-types` — listar (con filtro `include_inactive`) y `member_count` por tipo
- `POST /clubs/{id}/membership-types` — crear
- `PATCH /clubs/{id}/membership-types/{mt_id}` — editar (incl. activar/desactivar)
- `DELETE /clubs/{id}/membership-types/{mt_id}` — soft-delete (rechaza si hay miembros activos asignados, código 409)

**Backend — CRUD del padrón (Owner/Admin/Manager):**
- `GET /clubs/{id}/padron` — listar con filtros (`q`, `status_filter`, `membership_type_id`)
- `POST /clubs/{id}/padron` — agregar miembro por `email`/`username`/`user_id`. Si ya existe inactivo, reactiva.
- `PATCH /clubs/{id}/padron/{user_id}` — editar tipo, status (active/inactive/suspended), expiración, notas, # de socio
- `DELETE /clubs/{id}/padron/{user_id}` — soft-delete (status=inactive)

**Frontend — páginas nuevas:**
- `/[locale]/club/{id}/members` — padrón con tabla responsive, filtros (status, tipo, búsqueda), modal "Agregar" con formulario completo (email, # de socio, tipo, fechas ingresó/vence, notas), modal "Editar" para cambiar estado/tipo, botón "Dar de baja". Lectura disponible para Staff; CRUD para Manager+.
- `/[locale]/club/{id}/membership-types` — grid de tipos con cuota mensual/anual, member_count, badges activo/inactivo, modal crear/editar, toggle activar/desactivar, eliminar (con guard de miembros activos). Solo Owner/Admin.

**Frontend — panel del cliente (`/club/{id}`):**
- Reemplaza la sección "Próximamente" del padrón con **dos tarjetas activas**: "Padrón de miembros" (link a /members con contador) y "Tipos de membresía" (link a configuración).
- "Próximamente" queda solo con Tee times, Estados de cuenta, Empleados, Import CSV.

**Matriz de permisos implementada (primera vez):**

| Acción | Owner | Admin | Manager | Staff | Súper-admin |
|---|---|---|---|---|---|
| Ver padrón | ✓ | ✓ | ✓ | ✓ | ✓ |
| CRUD miembros | ✓ | ✓ | ✓ | — | ✓ |
| CRUD tipos de membresía | ✓ | ✓ | — | — | ✓ |
| Gestionar staff del club | ✓ | — | — | — | ✓ (vía /admin/clubs) |

### Notes

- Endpoint del padrón se llama `/padron` (no `/members`) para no chocar con el endpoint legacy B2C `/clubs/{id}/members` del jugador.
- Import CSV (masivo) queda para v1.11.x. Hoy se agregan miembros uno a uno por email/username.
- `member_count` en tipos se calcula on-demand; sin caché. Aceptable hasta cientos de miembros por club.

---

## [1.10.1] - 2026-05-15

### Added — Clubs SaaS Fase 0.5 — Panel del cliente y gestión de staff

Con v1.10.0 el súper-admin podía crear clubes, pero el administrador del club no tenía dónde entrar. Esta versión cierra ese gap.

**Backend (`/api/v1/clubs/*`):**
- `GET /clubs/staff/mine` — lista clubes donde el usuario actual es staff activo (owner/admin/manager/staff). Usado por el dashboard del jugador para detectar si tiene panel cliente-admin.
- `GET /clubs/{club_id}/dashboard` — info completa del club + miembros, staff_count, plan. Requiere ser staff del club o súper-admin.
- `GET /clubs/{club_id}/staff` — lista el staff del club. Mismo scoping.
- `POST /admin/clubs/{club_id}/staff` — aceptaba solo `user_id` UUID, ahora también acepta `email` o `username` en el body para facilitar la UI.

**Frontend:**
- Nueva página `/[locale]/club/[id]` — panel del cliente-admin: hero con nombre/slug/plan, métricas (miembros, staff, moneda, verificado), contacto, plan actual con renovación, lista de staff con roles coloreados, sección "Próximamente" anticipando Fase 1+.
- Dashboard del jugador (`/[locale]/dashboard`) detecta clubes donde el user es staff via `/clubs/staff/mine` y muestra un bloque azul **"Mi Club: {nombre}"** con su rol → enlaza al panel.
- `/[locale]/admin/clubs` añade botón **"Staff"** en cada tarjeta de club que abre modal con:
  - Lista de staff actual con avatar, email, rol (badges Owner/Admin/Manager/Staff coloreados)
  - Input para agregar staff por email o username + selector de rol → POST `/admin/clubs/{id}/staff`
  - Botón quitar (UserMinus) → DELETE
  - Banner explicativo: "el admin debe registrarse primero en golfbookvip.com"

**Flujo end-to-end ya funcional:**
1. Súper-admin crea el club desde `/admin/clubs`.
2. El admin del club crea su cuenta normal en `/auth/register`.
3. Súper-admin va a `/admin/clubs` → botón Staff → escribe email del admin del club + rol Owner → Add.
4. El admin del club hace login → su dashboard ahora muestra el bloque azul "Mi Club" → click → entra al panel.

### Notes

- Las features de gestión (padrón, tee times, cuentas) NO están en esta versión — solo visualización del club. La Fase 1 se enfocará en CRUD de miembros.
- El admin del club por ahora no tiene endpoints para crear/editar miembros — sigue siendo súper-admin only para evitar dar permisos antes de validar el modelo.

---

## [1.10.0] - 2026-05-15

### Added — Clubs SaaS MVP · Fase 0 — Infraestructura

Primer release del producto B2B **GolfBookVIP Clubs** (gestión SaaS para clubes de golf), junto al producto B2C existente para jugadores.

**Backend — endpoints súper admin (`/api/v1/admin/clubs/*`):**
- `GET /admin/clubs` — listar todos los clubes con búsqueda (`q`) e `include_inactive`. Devuelve `member_count` y `staff_count`.
- `GET /admin/clubs/plans` — listar `subscription_plans` disponibles (Free / Standard / Premium / Enterprise) para asignar a clubes.
- `POST /admin/clubs` — crear club con auto-slug desde el nombre (kebab-case + uuid corto si colisión). Acepta plan inicial opcional.
- `PATCH /admin/clubs/{club_id}` — actualizar metadata, plan, estado activo/inactivo.
- `POST /admin/clubs/{club_id}/staff` — agregar staff con rol (owner/admin/manager/staff).
- `DELETE /admin/clubs/{club_id}/staff/{user_id}` — quitar staff (desactivación lógica).

**Frontend — panel súper admin (`/admin/clubs`):**
- Botón "Clubes SaaS" en header del panel admin principal.
- Listado de clubes en grid responsivo con: nombre, slug-subdominio, plan actual (Free/Standard/Premium con colores), miembros, staff, estado, ciudad, contacto.
- Búsqueda por nombre/slug/ciudad + toggle "incluir inactivos".
- Modal "Nuevo club" con campos: nombre, ciudad, país, teléfono, email, plan inicial.
- Modal "Cambiar plan" para upgradear/degradear el plan de un club existente.
- Botón activar/desactivar club.
- Sección "Planes disponibles" mostrando catálogo con precios mensuales y límite de miembros.

**Bases que aprovecha (modelos pre-existentes en DB):**
- `clubs`, `club_staff`, `club_members`, `membership_types`, `member_accounts`, `account_transactions`
- `subscription_plans` con 6 planes pre-sembrados (free_player, player_pro, free_club, club_starter, club_pro, club_enterprise)
- `tee_time_slots`, `tee_time_bookings` (listos para Fase 2)

**Próximas fases (planeadas, no incluidas en esta release):**
- Fase 1 (5-7 días): Padrón de miembros (CRUD + import CSV)
- Fase 2 (7-10 días): Sistema de tee times + calendario admin
- Fase 3 (5-7 días): Estado de cuenta del miembro + PDF
- Fase 4 (3-5 días): Onboarding wizard + documentación

### Notes

- Multi-tenancy implementada por `club_id` en cada tabla del dominio club; sin schemas separados.
- White-label con dominio personalizado (Premium) queda planeado para Fase 4+ vía reverse proxy.
- Solo el súper admin (`is_superadmin=true`) puede crear/editar clubes desde este panel; el staff del club tendrá su propia UI más adelante.

---

## [1.9.3] - 2026-05-15

### Fixed — Estadísticas del perfil mostraban todo en cero

`GET /users/me/stats` leía de la tabla `PlayerStats` que se crea vacía en el signup pero nunca se actualiza al finalizar rondas. Resultado: rondas=0, birdies=0, mejor score=null, etc. aunque el usuario tuviera jugadas finalizadas.

**Fix:** reescrito el endpoint para **calcular on-demand** desde las tablas Score, RoundPlayer, CourseHole, ScoreDifferential, y RoundPlayerBalance. Ya no depende de PlayerStats persistido.

Stats calculadas:
- `total_rounds` — rondas finished donde participó como playing (no withdrawn, no observer)
- `total_holes` — suma de hoyos con score
- `avg_score` — promedio gross por hoyo
- `avg_putts_per_hole`, `avg_putts_per_round`
- `total_eagles` (incluye albatross y HIO en este conteo "águilas+"), `total_birdies`, `total_pars`, `total_bogeys`, `total_double_bogeys`, `total_worse`
- `total_hole_in_ones`, `total_three_putts`
- `best_score_18`, `best_score_9` (low score completo)
- `best_differential` (mínimo de ScoreDifferential)
- `total_bet_won`, `total_bet_lost` (suma de balances persistidos)

### Notes

- `fairways_hit_pct` y `gir_pct` quedan en `null` porque actualmente el modelo Score no trackea esos campos. Si quieres agregarlos, necesitamos columnas extra y captura en Play page.
- Cálculo on-demand es rápido para usuarios con <100 rondas. Si crece mucho, optimizamos con persistencia.
- PlayerStats sigue existiendo en la DB pero ya no se usa para este endpoint — quedará para uso futuro (cache opcional).

---

## [1.9.2] - 2026-05-15

### Fixed — Gráfica "Balance por mes" se veía deformada

El SVG tenía `preserveAspectRatio="none"` que estiraba el viewport y deformaba texto y barras. Reemplazado por **gráfica HTML/CSS** con flexbox:

- Línea cero horizontal al centro
- Barras positivas crecen hacia arriba con gradiente verde
- Barras negativas crecen hacia abajo con gradiente rojo
- Label de mes + año al pie ("May '26")
- Valor del balance arriba/abajo de cada barra
- Leyenda al fondo con colores
- Scroll horizontal si hay muchos meses
- Altura fija 200px (100px arriba + 100px abajo de la línea cero)

### Added — Backend bilingüe en `compute_balances`

`compute_balances(round_id, db, lang="es")` ahora genera los `detail` strings en el idioma solicitado. Todas las apuestas tienen versiones ES/EN:

```
ES: "Entry fee $20: pot $440 dividido 60/30/10 a low net"
EN: "Entry fee $20: pot $440 split 60/30/10 to low net"

ES: "Vidal hizo 4 birdies ($10 c/u) → cobra ..."
EN: "Vidal made 4 birdies ($10 each) → earns ..."

ES: "Hoyo 5: Vidal low net outright → +3 skins acumulados (carry desde H3, H4)"
EN: "Hole 5: Vidal outright low net → +3 accumulated skins (carry from H3, H4)"

ES: "Nassau Salida (1-9) $20: pot $440 → ganador(es) net 32"
EN: "Nassau Front 9 (1-9) $20: pot $440 → winner(s) net 32"
```

Cubre: entry_fee, nassau, per_hole, prize, penalty, skins (incluyendo línea de forfeit).

### Changed — Endpoint `/rounds/{id}/balances` acepta `?lang`

- Default: `es`
- Frontend ahora propaga `?lang={locale}` desde round detail y `/results` page
- Si tu app está en inglés, los detalles ahora vienen en inglés
- Si está en español, en español

### Notes

- `persist_balances` usa lang='es' por default — solo guarda NÚMEROS, los detalles se regeneran on-demand con el locale del cliente
- Los textos hardcoded del frontend (titles, labels, headers) ya estaban bilingües desde antes
- Esto cierra el último gap de bilinguismo en la sección Pérdidas y ganancias

---

## [1.9.1] - 2026-05-15

### Fixed — Lazy backfill no detectaba placeholders obsoletos

Bug: `/me/balance-history` no mostraba rondas finalizadas ANTES del despliegue de v1.9.0 porque:

1. Cuando se invita un jugador a una ronda, `invite_player` crea un row vacío en `round_player_balance` como placeholder (entry_fee=0, total=0, etc.) — esto es preexistente.
2. La condición de lazy backfill era `if bal is None: recompute` — pero el placeholder EXISTE con valores en cero, así que la condición fallaba.
3. Resultado: balances persistidos quedaban en cero forever para rondas finalizadas antes del despliegue.

Fix: la nueva condición detecta también placeholders obsoletos via `bal.updated_at < round.finished_at`:

```python
needs_recompute = (
    bal is None
    or (round_.finished_at and bal.updated_at and bal.updated_at < round_.finished_at)
)
```

Como los placeholders se crean en `invite_player` (antes de `finished`), su `updated_at` siempre es anterior a `finished_at` — el lazy backfill ahora los detecta y los recalcula correctamente.

### Impact

- Las rondas finalizadas antiguas ahora aparecen en el historial al primer query
- Las nuevas rondas finalizadas siguen persistiendo desde `finish_round` (no requieren backfill)
- Idempotente: recompute solo corre 1 vez (queda persistido con `updated_at >= finished_at`)

---

## [1.9.0] - 2026-05-15

Historial financiero personal — cada jugador ve su estado de cuenta con gráfica, desglose y PDF profesional.

### Added — Backend: persistencia de balances

- `app/services/balances.py` ahora expone `persist_balances(round_id, db)` y `delete_persisted_balances(round_id, db)`
- `finish_round` ahora persiste balances finales en `round_player_balance` cuando una ronda llega a `finished`
- `reopen_round` borra los balances persistidos (ya no son finales)
- Schema existente reusado con mapeo:
  - `entry_fee` → entry_fee, `nassau_balance` → nassau, `other_balance` → per_hole
  - `birds_earned` → prizes, `three_putt_loss` → penalties, `skins_balance` → skins
  - `oyes_balance` → oyes, `total_balance` → total
- **Lazy backfill**: si una ronda finished antigua no tiene balances persistidos, se calculan y guardan automáticamente la primera vez que se consultan via `/balance-history`

### Added — Endpoints historial financiero

- `GET /users/me/balance-history?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&limit=N`
  - Lista de rondas finalizadas donde participó el usuario con balance final
  - Filtro por fechas opcional
  - Solo incluye rondas con movimiento ≠ 0
  - Excluye rondas donde fue withdrawn/observer

- `GET /users/me/balance-summary?start_date=...&end_date=...`
  - Agregaciones del período:
    - `net_balance`, `total_won`, `total_paid`
    - `rounds_played`, `rounds_won`, `rounds_lost`, `rounds_tied`
    - `biggest_win`, `biggest_loss` (con detalle de ronda)
    - `chart_monthly`: array de `{month: YYYY-MM, total: float}` para gráfica
    - `by_bet_type`: acumulado neto por categoría (entry_fee, nassau, etc.)

### Added — Página `/profile/finances`

Nueva página accesible desde el botón "💰 Mi cuenta — Historial financiero" en `/profile`:

- **Filtros de fecha**: 6 presets (Todo, Este mes, Mes pasado, 3 meses, Año actual, Personalizado) + 2 date pickers
- **Banner de balance neto** prominente (verde si positivo, rojo si negativo, monto en 5xl)
- **8 stat cards**: rondas ganadas/perdidas/empate/total, total ganado/pagado, mejor jugada, peor jugada
- **Gráfica SVG mensual** de barras: verde positivas, rojo negativas, etiqueta de mes y monto
- **Desglose por tipo de apuesta**: acumulado neto del período por categoría
- **Tabla de historial**: filas clickeables, navega al detalle de la ronda
- **Botón PDF** que abre la versión imprimible
- Privacidad: cada usuario solo ve su propio historial

### Added — Página `/profile/finances/print` (PDF profesional)

Versión imprimible estilo estado de cuenta bancario:

- Header con brand + fecha de generación
- Título "Estado de cuenta" + nombre/email/username
- Línea de período seleccionado
- **Balance Banner grande** verde sólido si positivo, rojo sólido si negativo
- Tabla "Resumen" con 8 métricas
- **Gráfica SVG** de barras por mes con valores
- Tabla "Acumulado por tipo de apuesta" con fila TOTAL destacada amarillo
- Tabla "Historial por jugada" con fecha, torneo, curso, formato, balance
- Footer con timestamp y nota "Documento personal — confidencial"
- Print CSS Letter, page-break automático si excede
- Auto-print con `?autoprint=true`

### Notes

- Stats calculadas client-side desde el endpoint para máxima flexibilidad
- Las rondas ya finalizadas se backfillan en su primera consulta (sin script manual)
- Esto sienta base para futuras features: ranking de tesorero, alertas de pago pendiente, integración con métodos de pago

---

## [1.8.0] - 2026-05-15

Print modular + privacidad por jugador. Cada sección puede mandarse a imprimir/PDF de forma individual para compartir por WhatsApp/email, y los jugadores regulares ahora solo ven SU ticket personal — los detalles de otros jugadores quedan ocultos.

### Added — Privacidad por jugador (backend)

`GET /rounds/{id}/balances` ahora detecta el rol del que pide:

- **Creator o superadmin**: ve TODO (líneas completas con amounts de todos los jugadores, todas las vistas)
- **Jugador regular**: solo ve las líneas que le afectan, con amount filtrado a su propio monto. La lista de `players` (con totales) sí es visible para todos — necesaria para auditar la liquidación grupal.

Response incluye:
- `viewer_is_creator: boolean`
- `viewer_is_superadmin: boolean`
- `viewer_user_id: string`

### Changed — UI condicional por rol (round detail)

- Si soy **creator**: toggle "Por apuesta | Por jugador | Resumen" (3 vistas, sin restricciones)
- Si soy **jugador regular**: sin toggle. Solo se muestra **mi propio ticket** + **tabla Gran Total** general. Los movimientos detallados de otros (Nassau ganador, etc.) están ocultos.
- Badge "vista jugador" en el header para que sea claro el contexto

### Added — Menú de impresión modular en round detail

Nueva sección colapsable **"🖨️ Imprimir / PDF para enviar"** con botones agrupados por audiencia:

**Para todos** (público):
- 🏆 Leaderboard (posiciones)
- 🏅 Premios especiales

**Personal**:
- 👤 Mi ticket personal (ganó/pagó/total)

**Liquidación grupal**:
- 💰 Gran total por jugador

**Solo creator** (auditoría):
- 🎫 Entry Fee (detalle)
- 🎯 Nassau (detalle por segmento)
- ⛳ Por hoyo ganado
- 🏅 Premios (detalle birdies/eagles/HIO por jugador)
- ⚠️ Castigos (3 putts)
- 💎 Skines (hoyo por hoyo con carry-over)
- 👥 TODOS los tickets (uno por hoja)
- 👤 Ticket individual (selector dropdown de cualquier jugador)
- 📦 Paquete completo (master + tickets)

Cada botón abre nueva pestaña con URL como `/results?section=X&autoprint=true` que renderiza solo esa sección y dispara `window.print()` automáticamente al cargar.

### Added — `/results` acepta URL params

- `?section=leaderboard|premios|balances|gran-total|ticket|bet-entry_fee|bet-nassau|bet-per_hole|bet-prize|bet-penalty|bet-skins|all` → renderiza solo esa sección
- `?player=<user_id>` (para section=ticket) → solo el ticket de ese jugador
- `?autoprint=true` → dispara diálogo de impresión 600ms después de cargar

Suspense wrapping para que `useSearchParams` funcione correctamente en Next.js 16.

### Notes

- El menú de impresión NO requiere navegar — abre una pestaña independiente que se cierra después de imprimir/guardar
- Para enviar por WhatsApp: tap botón → Save as PDF → adjuntar el archivo
- La lógica de filtrado backend protege contra snooping vía DevTools — un jugador regular NO recibe los amounts de otros aunque inspeccione la respuesta del API
- Las cards `PlayerLedger` siguen mostrando movimientos como "Birdie de Vidal" en el `detail` text (eso es información pública del torneo). Lo privado son los DÓLARES individuales de otros jugadores.

---

## [1.7.10] - 2026-05-15

### Changed — Tabla "Gran Total" estilo recibo contable (fondo blanco)

Para que los positivos se vean en **negro literal** y los negativos en **rojo literal**, la tabla Gran Total ahora tiene fondo blanco como un recibo contable o estado de cuenta — el resto del dashboard mantiene el tema oscuro, la tabla destaca como un documento financiero.

- Fondo de la tabla: `bg-white` (era zinc-900 con gradiente verde/amarillo)
- Texto positivo: `text-black` sobre fondo blanco
- Texto negativo: `text-red-600` (rojo accounting clásico)
- Texto cero: `text-gray-400` (gris muted)
- Filas alternas: blanco/amarillo claro para top 1
- Header: fondo gris oscuro con texto blanco (alto contraste)
- Banner del título: amarillo dorado destacando el "GRAN TOTAL POR JUGADOR"

Visualmente queda como un ticket de caja en medio del dashboard — máxima legibilidad para auditar quién paga qué.

---

## [1.7.9] - 2026-05-15

### Changed — Color de valores en tabla Gran Total

Patrón financiero estándar: solo las pérdidas se resaltan, ganancias en color neutro.

- **Positivos** (ganaron): color neutro (`text-zinc-100` en pantalla / `#111` en impresión)
- **Negativos** (perdieron): rojo (`text-red-400` / `#b91c1c`)
- **Cero**: gris medio (`text-zinc-500`)

Antes los positivos estaban en verde llamativo, lo que hacía que TODAS las celdas con movimiento llamaran atención por igual. Ahora solo las pérdidas saltan visualmente — más fácil identificar quién debe pagar.

Aplicado en:
- Tabla "Gran total por jugador" del round detail (columnas + columna TOTAL)
- Tabla impresa en `/results` vista maestra

Las tarjetas "Por jugador" (ledger personal) mantienen GANÓ en verde y PAGÓ en rojo porque ahí la división por columna es deliberada y útil.

---

## [1.7.8] - 2026-05-15

### Fixed — Header de tabla Gran Total ilegible

Feedback de v1.7.7: el cambio anterior reemplazó los valores 0 por "—" pero el usuario prefería ver los $0.00. El problema real era el **color del header**, no los valores.

Correcciones:
- **`fmtMoney()` revertido** — vuelve a mostrar `$0.00` (no `—`)
- **Header row** `text-zinc-500` → `text-white` (mismo contraste que la columna TOTAL)
- Header row `bg-zinc-800/40` → `bg-zinc-800/60` para más contraste
- Font weight `font-semibold` → `font-bold` en todos los headers
- Abreviaciones expandidas a palabras completas:
  - `Entr.` → `Entrada`
  - `x Hoyo` → `Por hoyo`
  - `Prem.` → `Premio`
  - `Cast.` → `Castigo`
  - `Skines` se mantiene (ya completo)

Aplicado en round detail y en `/results` impreso.

---

## [1.7.7] - 2026-05-15

### Fixed — Ceros invisibles en tabla de balances

- En la tabla "Gran total por jugador" del round detail y en `/results` print, los ceros aparecían como `+$0.00` con color `text-zinc-700` (casi invisible sobre fondo oscuro)
- `fmtMoney()` ahora devuelve `—` cuando el valor es ~0 (más limpio y legible)
- `cellCls` para valores cero usa `text-zinc-500` (más contraste) por si acaso
- Aplicado tanto en pantalla como en versión impresa

---

## [1.7.6] - 2026-05-15

Ledger personal por jugador — cada uno ve su propio "estado de cuenta" con ganó/pagó/total.

### Added — Vista "Por jugador" en balances (round detail)

Toggle nuevo en la sección Pérdidas y ganancias con 3 vistas:
- **Por apuesta** (default actual): mini-tablas por tipo de apuesta
- **Por jugador** (NUEVO): una tarjeta por jugador con su ledger personal
- **Resumen**: solo la tabla de gran total (vista compacta)

**Tarjeta de ledger personal:**
- Header con nombre y HCP del jugador
- Grid de 2 columnas:
  - **GANÓ (+)** verde: lista de cada ingreso con descripción contextualizada e icono
  - **PAGÓ (−)** rojo: lista de cada salida
- Cada renglón muestra: ícono del tipo (🎫 🎯 ⛳ 🏅 ⚠️ 💎) + descripción adaptada al jugador + monto
- Subtotales al pie de cada columna
- **Banner TOTAL NETO** al fondo: verde si positivo (ganó), rojo si negativo (pagó)
- Mobile: cards apiladas / Desktop: grid 2 columnas

Las descripciones se contextualizan según el jugador. Ejemplos:
- Backend dice "Entry fee $20: pot $440 dividido 60/30/10" → Vidal ve "Entry fee — premio +$264" / otros ven "Aportación entry fee −$20"
- Backend dice "Vidal hizo 4 birdies..." → Vidal lo ve completo "Vidal Garza hizo 4 birdies (cobra $840)" / otros ven el mismo texto pero con su pago de −$40
- Skins: "Hoyo 5: Leo low net outright → +3 skins (carry desde H3, H4)" — todos ven el texto, cada uno con su monto

### Added — Tickets impresos por jugador en `/results`

Después del breakdown por apuesta y la tabla de gran total, ahora se imprime también **una tarjeta personal por cada jugador** con `page-break-before: always`. Resultado:
- Cada jugador puede recortar SU hoja y guardarla como ticket
- Header con posición (🏆🥈🥉 top 3) + nombre grande + HCP
- Grid GANÓ/PAGÓ con monto detallado
- Subtotales destacados (fondo amarillo)
- **Banner TOTAL NETO** grande al pie: verde sólido si ganó, rojo sólido si perdió

### Notes

- Vista "Por jugador" es transparencia personal — cada jugador ve exactamente cómo se calculó SU número
- Vista "Por apuesta" sigue siendo para auditoría general del tesorero
- Vista "Resumen" para validación rápida sin scroll
- En impresión, las 3 vistas se imprimen secuencialmente: auditoría general → gran total → tickets personales

---

## [1.7.5] - 2026-05-15

Más granularidad en el desglose de premios y skines.

### Changed — Premios desglosados por jugador

Antes: una sola línea agregada `"Birdies $10: cada uno paga al que lo hizo"` con el total.

Ahora: **una línea por cada jugador que hizo el evento**, con conteo explícito:
- `"Vidal Garza hizo 4 birdies ($10 c/u) → cobra $10 × 21 otros × 4 = $840.00"`
- `"Leo Glz hizo 2 birdies ($10 c/u) → cobra $10 × 21 otros × 2 = $420.00"`
- `"Enrique hizo 1 birdie ($10 c/u) → cobra $10 × 21 otros × 1 = $210.00"`
- (Aplica a Birdies, Eagles, Albatross, Hoyos en uno)

Cada línea muestra ganadores y pagadores con el monto exacto correspondiente a ese evento.

### Changed — Skines hoyo por hoyo

Antes: una sola línea agregada con todos los skines.

Ahora: **una línea por cada skin ganado** con detalle de carry-over:
- `"Hoyo 5: Vidal Garza low net outright → +1 skin = $105.00"`
- `"Hoyo 8: Leo Glz low net outright → +3 skins acumulados (carry desde H6, H7) = $315.00"`
- `"📋 2 skins forfeit (sin ganador al final del 18): empates en H17, H18"` (línea informativa, sin movimiento)

Ahora se ve exactamente:
- Qué hoyos generaron skins ganados
- Qué hoyos hubo empate (carry-over)
- Cuántos skins se acumularon antes del win
- Cuántos quedaron forfeit al final

### Notes

- Solo cambio backend (`app/services/balances.py`). El frontend ya manejaba múltiples líneas y líneas informativas naturalmente.
- El desglose hace MÁS LARGA la sección de premios y skines (ahora 1 línea por jugador/evento) pero la información antes era opaca.

---

## [1.7.4] - 2026-05-15

Transparencia total en las apuestas — el jugador puede ver las reglas de cada formato Y el desglose detallado de cómo se calculó su pérdida/ganancia.

### Added — Modal "Cómo funciona" en cada apuesta

En la sección de configuración de apuestas, cada tipo (Entry Fee, Nassau, Por hoyo, Premios, Castigos, Skines, Oyes) tiene un botón ℹ️ que abre un modal con:

- **Descripción detallada** de cómo opera la apuesta
- **Reglas específicas**: empates, carry-over, etc.
- **Ejemplo numérico** con cantidades reales para que se entienda visualmente
- Versión bilingüe ES/EN

Para que ningún jugador tenga duda de qué está aceptando.

### Changed — Tabla de balances reestructurada

Antes era una sola tabla con columnas. Ahora es:

1. **Header explicativo** "Pérdidas y ganancias — desglose detallado"
2. **Mini-tabla por cada tipo de apuesta** con:
   - Detalle textual de la línea (ej. "Nassau Salida (1-9) $20: pot $440 → ganador net 35")
   - Sección "Ganaron" (verde) con jugadores y montos
   - Sección "Pagaron" (rojo) — agrupada cuando son varios al mismo monto ("18 jugadores · −$20 c/u")
3. **GRAN TOTAL POR JUGADOR** al final — tabla con medallas 🏆🥈🥉, columnas con cada tipo y total resaltado, fondo dorado

### Changed — Print balances pro detallado

Misma estructura en `/results` vista maestra para impresión:
- Grid 2 columnas con mini-bloques por tipo de apuesta
- Cada bloque con detalle de movimientos
- Tabla "GRAN TOTAL" al final con columna de cada tipo y suma resaltada
- Imprimible junto con leaderboard y premios especiales

### Notes

- Los modals usan el array `lines` que ya devolvía el backend en `/balances` — sin cambios al motor
- Detalles textuales generados en backend (`detail` field): cada línea explica QUÉ ganó/perdió cada jugador y por qué
- "Oyes" tiene su modal con la nota de pendiente regla regional

---

## [1.7.3] - 2026-05-15

Motor de pérdidas y ganancias + fix de spinner stale al finalizar.

### Added — Motor de balances de apuestas

Nuevo servicio `app/services/balances.py` calcula pérdidas y ganancias por jugador al cierre de la ronda según la configuración de apuestas. Reglas implementadas (estándares de la mayoría de ligas):

- **Entry fee**: pot total dividido 60/30/10 a los 3 mejores NET
- **Nassau F9 / B9 / Total**: cada segmento es un pot independiente, ganador low NET toma todo, empate split
- **Por hoyo ganado**: cada hoyo low NET cobra `per_hole_bet` de cada jugador que perdió; empate split entre ganadores
- **Birdie / Eagle / Albatross / HIO**: cada uno cobra del resto al jugador que lo hizo (pay-each-other), multiplicado por cantidad de eventos
- **3-putt penalty**: cada 3-putt el penalizado paga al resto
- **Skins** (con carry-over en empate): cada skin paga `skins_value × (N-1)` al ganador. Gross o net según `skins_use_net`. Sin ganar al final del 18 = forfeit
- **Oyes**: pendiente (necesito que me confirmes regla regional)

Excluye automáticamente jugadores withdrawn y observers.

### Added — Endpoint `GET /rounds/{id}/balances`

Devuelve por jugador el desglose: `entry_fee`, `nassau`, `per_hole`, `prizes`, `penalties`, `skins`, `oyes`, `total`. Más una lista de `lines` con explicación textual de cada movimiento.

### Added — Sección "Pérdidas y ganancias" en round detail

Tabla compacta con jugadores ordenados por total desc (ganadores arriba). Color verde para ganancias, rojo para pérdidas, neutro para zero. Columna TOTAL resaltada amarillo. Cita de reglas al pie.

### Added — Balances impresos en `/results`

Vista maestra ahora incluye sección "Pérdidas y ganancias" con la misma tabla optimizada para impresión (filas top con fondo amarillo, regla al pie). Imprimible junto con leaderboard y premios especiales.

### Fixed — Spinner stale en "Terminar ronda"

Si el servidor regresa 400 con detalle "No se puede finalizar" (porque la ronda ya cambió de estado por otra vía o doble-click), el frontend ahora hace auto-refresh en lugar de mostrar error. Sincroniza UI con estado real del servidor.

### Notes

- **Reglas son configurables a nivel de futuro**: cualquier liga puede tener variantes. Si tu liga difiere (ej. otros porcentajes del entry fee, Nassau con presses, oyes con reglas específicas), las parametrizamos
- Necesito que confirmes la regla de **Oyes** (regional mexicano) para implementarla en v1.7.4

---

## [1.7.2] - 2026-05-14

### Added — Reset con limpiezas opcionales

Hasta ahora el reset solo borraba scores y mantenía grupos/equipos/capturistas. Para probar diferentes formatos (Stroke → Florida → Match) hay que limpiar también esos elementos. Agregamos 3 checkboxes opcionales al modal de reset:

- ☐ **Borrar grupos de salida y hoyos de inicio** (tee_group + starting_hole por jugador)
- ☐ **Borrar equipos (Florida) y pairings (Match)** (team_number + tee_order + match_order + flag teams_published)
- ☐ **Borrar capturistas designados** (is_group_scorer)

Si dejas todo sin marcar → comportamiento previo (solo scores, iteración rápida del MISMO formato).

Backend: `POST /rounds/{id}/reset?clear_tee_groups=true&clear_teams=true&clear_scorers=true` — flags independientes, combinables.

WS `round_reset` broadcast incluye el objeto `cleared` con los flags aplicados.

### Notes

- Lo que siempre se mantiene: jugadores invitados, course, apuestas, formato, HCP por jugador (sigue intacto, solo se borra el course_handicap si ese tee_group se borra)
- Caso de uso típico: terminé prueba de Florida, quiero probar Stroke → reset con checkbox "equipos" marcado limpia el setup de equipos sin tocar grupos de salida (que sí siguen sirviendo)

---

## [1.7.1] - 2026-05-14

### Added — Vista Matriz en "Tarjeta en curso"

Nueva vista que muestra **TODOS los jugadores con sus scores hoyo-por-hoyo simultáneamente** en una tabla compacta. Resuelve el caso de torneo con 20+ jugadores donde antes solo se veía la tarjeta de uno a la vez.

- Toggle "Detalle · Matriz" en el header del scorecard (creator o cualquier visualizador)
- **Detalle** (default): leaderboard + scorecard del jugador seleccionado (comportamiento previo)
- **Matriz** (nueva):
  - Columna sticky izquierda con posición + nombre + medalla top 3
  - Columna HCP
  - 18 columnas de hoyos con score gross
  - Columna "S" (suma salida 1-9) y "V" (suma vuelta 10-18) en 18 hoyos
  - Columna Tot + ±Par
  - Filas Par y SI debajo del header de hoyos
  - **Celdas coloreadas por resultado**:
    - 🟡 Eagle+ (-2 o mejor): fondo ámbar
    - 🟢 Birdie (-1): fondo verde
    - ⚪ Par (0): neutro
    - 🟠 Bogey (+1): naranja
    - 🔴 Doble o peor (+2 o más): fondo rojo
  - Scroll horizontal en móvil, ajusta a desktop sin scroll
  - Ordenado por gross asc (o stableford pts desc según formato)

### Notes

- Vista universal — funciona en stroke, stableford, skins, match, florida
- Para Match Play sigue habiendo una matriz de match propia que se usa cuando hay `matchups` (esa tiene resultado pareado, no totales)
- En desktop la matriz ocupa el ancho disponible; en móvil se desliza horizontal

---

## [1.7.0] - 2026-05-14

Responsive desktop layouts en las pantallas más usadas. Mobile sin cambios — solo se agregan estilos que aplican a partir de ≥1024px (lg:) y ≥1280px (xl:). Se aprovecha pantalla grande sin sacrificar la experiencia móvil.

### Fixed — Leaderboard sin scroll interno colgado

- Removido `max-h-72 overflow-y-auto` del leaderboard de jugadores en round detail
- Antes: lista clipped a 288px → solo se veían 5-6 de 22, los demás escondidos en scroll interno (confuso)
- Ahora: lista vertical completa, todos los 22 visibles, scroll normal de la página

### Changed — Round detail: layout 2 columnas en lg

- Main container `max-w-4xl` → `max-w-4xl lg:max-w-7xl` (de 896px a 1280px en escritorios grandes)
- Sección "Tarjeta en curso" en lg: **grid 3 columnas con divider**:
  - Col 1 (1/3): Leaderboard vertical con los 22 jugadores
  - Cols 2-3 (2/3): Scorecard detallado del jugador seleccionado, hoyo por hoyo
- Mobile: stack vertical idéntico al actual (leaderboard arriba, scorecard abajo)
- Hint contextual cambia según device: "Click para ver detalle →" (desktop), "Toca uno" (móvil)

### Changed — Dashboard responsive

- Stats cards: 1 columna móvil → 3 columnas desktop (sin cambio en este release)
- Quick access cards (Canchas, Clubs, Activity, Players, Groups): 2 cols móvil → **3 cols en lg, 4 cols en xl** (mejor aprovechamiento de pantallas anchas)

### Changed — Round list responsive

- Container `max-w-4xl` → `max-w-4xl lg:max-w-7xl`
- Lista de rondas: stack móvil → **grid 2 cols en lg, 3 cols en xl** — ver más rondas al mismo tiempo en escritorios

### Notes

- Patrón aplicado consistentemente: `mobile-default lg:desktop-style` (Tailwind responsive breakpoints)
- Cero cambios visuales en móvil — verificado con typecheck + build
- Print CSS y rutas `/tee-cards` `/results` no afectadas (esas son hojas A4/Letter independientes)

---

## [1.6.0] - 2026-05-14

Resultados pro + visibilidad de jugadores en scorecard. Bundle pensado para torneos de 22+ jugadores donde se necesita ver a todos al mismo tiempo y poder imprimir resultados con detalle profesional.

### Changed — Scorecard en round detail: tabs horizontales → leaderboard vertical

- Reemplazada la fila de tabs horizontales con scroll lateral (escondía 16 de 22 jugadores) por **lista vertical leaderboard** con todos visibles
- Cada fila muestra: posición (medallas oro/plata/bronce en top 3), nombre completo, HCP, Thru, Gross, vs Par con color por to-par
- Click en una fila → selecciona y muestra el scorecard hoyo-por-hoyo de ese jugador abajo
- `max-h-72 overflow-y-auto` permite scroll vertical limpio si hay más de ~9 jugadores
- Counter "Jugadores (N)" en el header de la sección

### Added — Página `/rounds/[id]/results`

Nueva ruta con dos vistas conmutables + botón Imprimir:

**Vista "Maestra"** (1 hoja, formato Letter, para tablón del clubhouse):
- Header: brand · fecha · torneo · curso · formato · par/CR/Slope
- **Winner banner** dorado con trofeo, nombre y score grande
- **Tabla de posiciones** completa: POS · Jugador · HCP · Gross · vs Par · Net · Pts · Thru. Winner row resaltada con fondo amarillo
- **Sección "Premios especiales"** (best of awards) con grid 2 columnas:
  - 🎯 Mejor gross
  - ⚡ Mejor net
  - 🏅 Mejor stableford
  - 🐦 Más birdies
  - 🎖 Más pars
  - ⬆️ Mejor salida (1-9)
  - ⬇️ Mejor vuelta (10-18)
  - 🎯 Mejor par 3 / par 4 / par 5 (sumas por categoría)
  - ⚪ Score más bajo en un hoyo
  - 🦅 Eagles o mejor (lista, fondo púrpura)
  - ⛳ HOLE IN ONE (lista, fondo rojo)

**Vista "Tarjetas"** (1 hoja por jugador, para entrega individual):
- Header del torneo
- **Bloque player-header**: posición ordinal grande con medalla si top 3, nombre, HCP/C-HCP/tee · totales Gross/Net/vs Par/Pts a la derecha
- Scorecard hoyo-por-hoyo (Salida + Vuelta) con par/SI por hoyo
- Cada celda de gross **coloreada según resultado**: eagle (amarillo), birdie (verde), par (neutro), bogey (naranja), double+ (rojo)
- Filas Net y Stableford (si aplica) abajo
- **Performance grid**: Eagles · Birdies · Pars · Bogeys · Dbl+ con números grandes
- Espacios para firma jugador / marker

### Added — Botón "📊 Imprimir resultados" en round detail

- Aparece cuando `status === 'finished'` o `'pending_validation'`
- Color púrpura, ícono 📊
- Navega a `/rounds/[id]/results`

### Notes

- Stats calculadas client-side desde `/scoreboard` — no requiere endpoints nuevos
- Print CSS con `@page { size: letter; margin: 0 }` y page-breaks entre tarjetas
- Excluye automáticamente jugadores withdrawn y observers de leaderboards y premios

---

## [1.5.2] - 2026-05-14

### Fixed — Spinner colgado en acciones de ronda

- `handleFinishRound`, `handleReopenRound`, `handleResetRound`, `handleAutoFill` ahora apagan el spinner del botón **inmediatamente** después del 200 OK del POST, antes de hacer el `load()` que recarga los datos
- El reload corre en background con `.catch()` silencioso
- **Por qué:** con 58 jugadores, el reload de `/scoreboard` + `/players` + otros endpoints puede tomar varios segundos. Si la red flaqueaba durante el reload, el spinner quedaba colgado aunque el servidor ya había completado la acción
- **Comportamiento ahora:** el botón se libera de inmediato; si el reload falla, el usuario solo necesita refrescar la página (la acción del servidor ya está confirmada)

---

## [1.5.1] - 2026-05-14

### Added — Creator override en captura

- `POST /scores` ahora permite al **creador de la ronda** capturar para CUALQUIER jugador, incluso si el grupo tiene scorer designado y el grupo es distinto al suyo. Override de organizador (útil para torneos: la mesa de control puede capturar por cualquiera ante emergencias)
- En el Play page, si `amCreator`, los inputs siempre quedan habilitados y NO aparece banner azul de observador

### Added — Auto-fill de scores (testing)

- `POST /rounds/{id}/dev/fill-scores` — creator only, status `active` o `scheduled`:
  - Borra scores existentes (idempotente)
  - Por cada jugador activo (excluye withdrawn/observers) genera un gross por cada hoyo
  - Distribución sesgada por hándicap del jugador:
    - HCP ≤9: birdie 12% · par 45% · bogey 30% · doble 10% · otros 3%
    - HCP 10-18: birdie 6% · par 35% · bogey 40% · doble 15% · otros 4%
    - HCP ≥19: birdie 3% · par 25% · bogey 38% · doble 25% · otros 9%
  - Putts estimados por diferencia vs par
  - Calcula net + flags + stableford via `scoring_svc.apply_score_to_model`
  - Si la ronda estaba `scheduled`, la mueve a `active`
  - Broadcast WS `scores_autofilled`
- Botón amarillo "🎲 Auto-rellenar scores (prueba)" en round detail (creator, active/scheduled). Confirmación previa con texto explícito

### Notes

- Auto-fill es para iteración de pruebas — permite generar 58 × 18 = 1044 scores en segundos
- Combinado con el reset de v1.5.0, el flujo de testing queda: configurar 1 vez → auto-fill → finalizar → ver leaderboard/balance/etc. → reset → repetir
- El creator override es feature **de producción** también (no solo testing)

---

## [1.5.0] - 2026-05-14

Testing toolkit: reset agresivo + cambio de formato sobre la marcha. Diseñado para que el creator pueda iterar pruebas con la misma ronda (ej. "58 primaveras") y probar todos los formatos sin tener que crear rondas nuevas para cada caso.

### Added — Reset agresivo

- `POST /rounds/{id}/reset` (creator-only, cualquier estado):
  - Borra: scores, balances, resultados de apuestas por hoyo, firmas de validación
  - Resetea: withdrawals y participant_mode='playing' por todos los jugadores
  - Borra: `ScoreDifferential` generados por la ronda y **recalcula HCP de los afectados** (revierte el impacto en tu hándicap de prueba)
  - Recrea balances vacíos por jugador
  - `Round.status='scheduled'`, `started_at/finished_at=null`
  - Mantiene: jugadores invitados, grupos de salida, capturistas designados, config de apuestas, formato, course, plantilla de pares
  - Broadcast WS `round_reset`
- Botón rojo "🗑️ Reiniciar (prueba)" en round detail, visible para creator cuando status ≠ 'scheduled'
- **Modal con doble protección**: requiere tipear literalmente `RESETEAR` para habilitar el botón final + lista clara de qué se borra y qué se mantiene

### Added — Cambio de formato sobre la marcha

- `PATCH /rounds/{id}/format` con body `{game_format: ...}` (creator-only, cualquier estado excepto `finished`)
- Dropdown selector visible en round detail (donde antes solo había badge con info-tooltip) — para el creator cuando la ronda no está finalizada
- Confirmación rápida antes de cambiar: "Los scores se preservan; solo cambia cómo se calculan los resultados"
- Útil para pasar de Stroke → Stableford (mismo gross, diferente cálculo) sin re-capturar
- Broadcast WS `format_changed`

### Notes

- El reset NO borra a los jugadores invitados ni los grupos/capturistas — perfecto para iteración con el mismo roster
- El cambio de formato a Match o Florida puede requerir reconfigurar pairings/equipos por separado (esos formatos tienen estructura adicional)

---

## [1.4.2] - 2026-05-14

### Changed — Marca de strokes en scorecard impresa

- Reemplazado el punto rojo (•) dentro de la celda — estorbaba al anotar el score manuscrito
- Ahora se marca con **línea roja en el borde inferior** de la celda:
  - 1 stroke recibido → `border-bottom: 3px solid red`
  - 2 strokes (C-HCP > 18) → `border-bottom: 5px double red`
- Es la convención de las cards profesionales de torneo (no invade el espacio de captura)
- Glosario actualizado: "marcados con línea roja al pie de la celda"

---

## [1.4.1] - 2026-05-14

### Added — Glosario en tarjeta de salida

- Bloque pequeño entre la sección de firmas y el footer con definiciones cortas para jugadores nuevos:
  - **HCP**: Handicap Index — tu hándicap WHS general
  - **C-HCP**: Course Handicap — ajustado al campo/tee (CR & Slope)
  - **SI**: Stroke Index — dificultad del hoyo (1 = más difícil, 18 = más fácil). Recibes strokes en los SI bajos según tu C-HCP
  - **Marker**: otro jugador del grupo que verifica y firma tu tarjeta al final
- Layout: grid 2 columnas, fuente 7.5pt, sutil borde discontinuo arriba para separarlo de las firmas

---

## [1.4.0] - 2026-05-14

Hoja de salida imprimible profesional. Tarjetas individuales por grupo + vista maestra. Diseñado para que un torneo pueda imprimir las tarjetas oficiales, entregarlas a cada grupo, y tener una maestra para el tablón del clubhouse.

### Added — Página `/rounds/[id]/tee-cards`

- **Vista "Tarjetas"** (default): una tarjeta por grupo, A4/Letter, lista para imprimir:
  - Header: GolfBookVIP brand · fecha legible
  - Nombre del torneo en titular grande
  - Curso + ciudad/estado · formato · hoyos · par total · CR/Slope
  - Banner del grupo: GRUPO N + SALIDA hoyo X
  - Línea del capturista designado (🎯)
  - Tabla de jugadores: nombre · HCP index · Course HCP · color de tee (con punto visual) · línea para firma
  - Scorecard grid completa: Salida 1-9 + Vuelta 10-18, par y SI por hoyo
  - **Strokes recibidos marcados con puntos rojos** según `floor(C-HCP/18) + ((C-HCP mod 18) >= SI ? 1 : 0)`
  - Totales: par salida + par vuelta + par total
  - Espacios para reglas locales y firma del jugador / marker
  - Footer con timestamp de generación

- **Vista "Maestra"**: una sola hoja con tabla compacta de TODOS los grupos:
  - Para el organizador / tablón del clubhouse
  - Columnas: Grupo · Hoyo · Jugadores (con HCP/C-HCP) · Capturista
  - 1 fila por grupo, todos en una sola hoja

- **Toolbar (no se imprime)**: switch entre vistas + botón "🖨️ Imprimir" + tip para desactivar headers del navegador

- **Print CSS**: `@page { size: letter; margin: 0 }`, `page-break-after: always` entre tarjetas, oculta toolbar/nav, fondos blancos limpios

### Added — Botón en round detail

- En sección "Grupos de salida" (vista no-edit), botón "🖨️ Imprimir hoja de salida" navega a `/tee-cards`. Visible solo cuando hay grupos configurados.

### Changed — Backend

- `GET /rounds/{id}/tee-groups` y respuesta del `PUT` ahora incluyen:
  - `handicap_index` (de RoundPlayer.handicap_index o User.handicap_index como fallback)
  - `tee_color` por jugador
  - Sin cambios al schema, ya existían los datos

### Notes

- Implementación HTML + print CSS (no PDF server-side). El usuario imprime desde el navegador y puede "Guardar como PDF" para archivar
- Funciona en cualquier impresora (no requiere fonts custom)
- Bonus: la maestra también se imprime con la misma acción

---

## [1.3.0] - 2026-05-14

Grupos de salida preparados para torneo. Cap subido de 6 → 18 grupos (capacidad para 72 jugadores en campo lleno), auto-asignación por hándicap, shotgun start automático y mejoras UX. Diseñado para que la lógica se reutilice cuando el módulo de Clubs convoque torneos.

### Added — Capacidad torneo

- Tope de grupos: 6 → **18 grupos** (capacidad para campo lleno: 18 grupos × 4 jugadores = 72 jugadores)
- Selector numérico stepper [-] [N] [+] reemplaza los botones [1-6] anteriores
- Helper "hasta N jugadores (4/grupo)" debajo del stepper

### Added — Acciones rápidas (creator only)

- 🎯 **Auto por hándicap**: ordena jugadores por `course_handicap` ascendente y los distribuye en bandas de `ceil(total / numGroups)` jugadores. Low HCP juntos, mid juntos, high juntos. Útil para flights de torneo.
- ⛳ **Shotgun start**: cada grupo arranca en su mismo número de hoyo (Grupo 1 → Hoyo 1, Grupo 18 → Hoyo 18). Estándar de torneos profesionales donde todos salen al mismo tiempo desde hoyos distintos.
- 🧹 **Vaciar grupos**: limpia toda la asignación con confirmación, regresa numGroups a 1.
- Contador "X/Y jugadores asignados" siempre visible

### Added — UI escalable

- Si numGroups ≤ 6 → botones (UI clásica)
- Si numGroups > 6 → **dropdown selector** por jugador (más manejable con muchos grupos)
- Lista de jugadores con `max-h-96 overflow-y-auto` para que no se haga infinita
- Grid de hoyos de salida pasa a 4 columnas si numGroups > 9

### Added — Validación visual

- Badge "X/4" por grupo en la sección de hoyos de salida
- Color: gris (incompleto) · emerald (lleno = 4) · rojo (sobrecargado >4)
- Warning visual, NO bloqueo — admite 5 jugadores ocasionales

### Notes

- Las acciones rápidas (auto-HCP, shotgun, vaciar) son client-side por simplicidad — modifican el `teeGroupDraft` state y el usuario presiona "Guardar grupos" para commitear vía PUT existente
- Cuando el módulo Clubs llegue, puede reutilizar la misma lógica desde su propia UI invocando PUT /rounds/{id}/tee-groups (sin cambios al backend)
- Backend acepta tee_group como Integer sin tope — no requirió migración

---

## [1.2.0] - 2026-05-14

Captura única por grupo + validación de tarjetas al cierre. Feedback de la ronda real del 12-may: necesitamos un único capturista por grupo (no cualquiera del grupo), modo observador para los demás, transferencia ante imprevistos en campo (batería muerta, retiro), y firma electrónica de cada jugador antes del cierre definitivo.

### Added — Capturista único por grupo

- DB: `round_players.is_group_scorer BOOLEAN DEFAULT FALSE` + unique index `(round_id, tee_group) WHERE is_group_scorer = TRUE` (máximo 1 scorer por grupo)
- `PATCH /rounds/{id}/players/{user_id}/set-scorer` — creator designa al capturista (quita el flag a los otros del mismo grupo)
- `POST /rounds/{id}/players/me/claim-scorer` — cualquier miembro del grupo toma el control (caso "se le acabó la batería al scorer")
- `POST /scores` enforcement: si el grupo tiene scorer designado, solo ese scorer puede capturar (incluso sus propios scores)
- Broadcast WS `scorer_changed` para que toda la UI del grupo se actualice en tiempo real

### Added — Vista observador en Play page

- Banner azul `👁 Observando captura de {nombre}` para no-scorers
- Inputs ± deshabilitados (visualmente atenuados, cursor not-allowed)
- Pickup oculto en modo observador
- Botón "Guardar hoyo" reemplazado por `⏳ Esperando captura de {nombre}…`
- Banner verde `🎯 Eres el capturista del grupo` para el scorer, con botón "Ceder"
- Modal de transferencia: el scorer cede el rol a otro miembro del grupo (lista de mates con botón Asignar →)
- Botón "Tomar control" para observadores (caso emergencia, con confirmación)

### Added — UI tee-groups con designación de capturista

- En `/rounds/[id]` sección "Grupos de salida": botón 🎯 por jugador (creator-only) para designarlo capturista
- Badge `🎯 Capturista` junto al nombre del scorer actual
- Refresh automático al cambiar scorer

### Added — Validación de tarjeta al cierre (firma electrónica)

- DB: `round_players.score_validated_at TIMESTAMPTZ NULL`
- Nuevo status `pending_validation` entre `active` y `finished`
- `POST /rounds/{id}/finish` con flujo nuevo:
  - Si hay scorer designado y status='active' → mueve a `pending_validation` + broadcast WS `pending_validation`
  - Si status='pending_validation' → verifica firmas; HTTP 409 con `code:pending_validations` si faltan; con `force=true` cierra de todos modos
  - Si NO hay scorer (ronda legacy) → cierra directo (comportamiento previo)
- `POST /rounds/{id}/players/me/validate-scorecard` — jugador firma su tarjeta, broadcast WS `scorecard_validated`
- Nueva ruta `/rounds/[id]/validate`: muestra resumen Gross/Net/vs par + scorecard hoyo-a-hoyo + estado de firmas del grupo + botones "Firmar tarjeta" / "Reportar diferencia"
- En el detalle de la ronda: botón "Cerrar definitivo" reemplaza a "Terminar ronda" cuando status='pending_validation' + link "Firmar tarjeta" prominente
- Auto-redirect a `/validate` cuando los jugadores reciben el WS `pending_validation` (estaban en Play page)

### Changed — Round detail

- Botón "Finalizar ronda" → "Terminar ronda" (en `active`) o "Cerrar definitivo" (en `pending_validation`) con estilo emerald
- Manejo nuevo de error 409 `pending_validations` con confirmación

### Notes

- Backward compatible: rondas sin scorer designado siguen funcionando como antes (cualquiera del grupo captura, finish va directo a finished)
- Migración aplicada en producción con `ALTER TABLE` directo

---

## [1.1.2] - 2026-05-13

Fix UX: el creador no podía modificar las apuestas una vez iniciada la ronda. El backend lo permitía, pero la UI tenía gating innecesario contra `status === 'scheduled'`.

### Fixed

- Inputs de apuestas (entry fee, Nassau, per hole, premios especiales, oyes, skines) ahora se quedan editables mientras `round.status !== 'finished'` — antes se bloqueaban al iniciar la ronda
- Botón "Guardar apuestas" visible también en rondas activas (antes solo en `scheduled`)

### Added

- Banner ámbar de advertencia cuando el creador edita apuestas con la ronda en curso: avisa que cambios pueden no aplicar a hoyos ya jugados (relevante para skines acumulados, Nassau front 9 ya cerrado, etc.)

### Notes

- Backend `POST /rounds/{id}/bet-config` ya permitía esto (solo valida ownership del creador, no status). La restricción era puramente cliente.

---

## [1.1.1] - 2026-05-13

UX: acceso discoverable al panel de administración para superadmins desde el dashboard. Antes había que conocer la URL `/admin/` directamente.

### Added — Acceso al admin para superadmins

- Icono escudo verde 🛡️ en el header del dashboard (junto a la campana de notificaciones) — visible solo si `user.is_superadmin === true`
- Card prominente "Panel de administración" debajo del welcome del dashboard — mismo gating

### Changed — API

- `UserOut` schema ahora expone `is_superadmin: bool = False` (campo siempre presente, default false para jugadores normales)
- `GET /users/me` ahora incluye el flag en la respuesta para que el frontend pueda condicionar UI

### Notes

- La seguridad real sigue siendo backend (`_require_admin()` en endpoints). El gating del frontend es UX, no defensa
- Jugadores normales NO ven el botón ni el card — el flag siempre llega como `false` para ellos

---

## [1.1.0] - 2026-05-13

Herramientas de superadmin desde feedback de la primera ronda real (12-may): jugadores que olvidan contraseña + necesidad de corregir hándicaps inflados por rondas de prueba.

### Added — Edición de hándicap desde panel admin

- `PATCH /admin/users/{user_id}` — actualiza `handicap_index` (rango -10 a 54, o `null` para borrar)
- Botón ✏️ por fila en `/admin/` → modal con input numérico, paso 0.1, validación cliente y servidor
- Aplica a cualquier usuario (incluso superadmin) — al usar el panel se sobreescribe sin recalcular diferenciales históricos

### Added — Reset de contraseña asistido por admin

- `POST /admin/users/{user_id}/reset-link` — superadmin genera token HMAC de 1h para un jugador
- Botón 🔑 por fila en `/admin/` (solo usuarios activos) → genera link, lo copia al portapapeles automáticamente y abre modal con el link completo para revisión/recopia manual
- Pensado para WhatsApp: admin manda el link, jugador lo abre, escribe nueva contraseña
- Token se invalida automáticamente al cambiar la contraseña (HMAC depende del hash actual)

### Notes

- SMTP real sigue pendiente para flujo self-service de "olvidé contraseña" — esto cubre el gap operativo mientras tanto

---

## [1.0.1] - 2026-05-12

Hotfix de seguridad. Rotación de credenciales de Firebase tras detectar la llave comprometida en historia git.

### Security

- Rotada llave de servicio Firebase `02e0dfbc6c...` → nueva llave `860d0f18082d...` (revocada manualmente en Firebase Console → Service Accounts)
- Llave nueva desplegada en `/opt/golfbookvip/firebase-credentials.json` del servidor y verificada dentro del container `golfbookvip_api`
- Backup local `firebase-credentials.json.OLD.*` eliminado del servidor tras confirmación de revocación

### Changed

- `.gitignore` endurecido con patrones `*firebase-adminsdk*.json`, `*service-account*.json`, `*-credentials.json`, `firebase-credentials.json.OLD.*` para prevenir futuros leaks de credenciales por descarga directa desde Firebase Console
- Footer del frontend ahora muestra `v1.0.1`

### Notes

- La llave vieja sigue presente en la historia git del commit `588c33a`, pero está revocada — recuperarla del historial no la reactiva en Firebase

---

## [1.0.0] - 2026-05-11

Primera release estable. 23 commits en una sesión: reescritura mayor del Play page, motor de captura por grupos, GPS, admin de canchas, leaderboard PGA-style, modo offline.

### Added — Grupos de salida + captura cruzada + conflictos

- DB: `round_players.tee_group`, `starting_hole`, `match_order`
- DB: `scores.entered_by`, `conflict_score`, `conflict_entered_by`, `has_conflict`
- DB: `users.is_superadmin`
- `POST /scores` acepta `for_user_id` (captura cruzada); valida mismo `tee_group` solo si la ronda usa grupos; detecta conflictos entre capturistas
- `GET/PUT /tee-groups`, `GET /conflicts`, `POST /scores/{hole}/resolve`
- `POST /finish` devuelve `409` si hay conflictos o scorecards incompletos (cliente repite con `?force=true`)
- `POST /rounds/{id}/reopen` — el creador puede reabrir una ronda finished, revierte ScoreDifferentials y recalcula HCP
- Broadcast WS: `score_conflict`, `conflict_resolved`, `round_reopened`, `player_withdrawn`
- Panel superadmin en `/admin/`

### Added — Play page reescrita: fila por jugador

- Lista vertical de filas (yo + compañeros) en lugar de selector + ± único
- Cada fila: nombre + HCP + estado + ± propio + score grande con etiqueta (Birdie/Par/Bogey…)
- "Guardar hoyo" hace POST en paralelo (`Promise.allSettled`) para todas las filas dirty
- Auto-avance al siguiente hoyo cuando todos guardaron
- Vista "Tarjeta" multi-jugador estilo papel: 1-9 Salida / 10-18 Vuelta, par+SI, colores por diff vs par, mi fila resaltada
- Putts solo en mi fila (estadística personal)

### Added — Marcador (leaderboard) PGA/Masters TV

- Columnas: POS · JUGADOR · TOT · GROSS · THRU
- Medallas oro/plata/bronce, empates con `T2`/`T3`
- Auto-orden: to-par asc, sin empezar al final, WD/observer al final con opacity-60
- Botón "Marcador" condicional según `game_format`

### Added — Retiro (WD) y modo observador

- DB: `round_players.withdrawn_at`, `withdrawn_reason`, `participant_mode`
- `POST /players/{uid}/withdraw` y `/unwithdraw` (creator o self)
- `POST /players/{uid}/set-mode` (`playing`/`observer`)
- `finish_round` skip de WD y observers en incomplete check y HCP recalc
- UI: menú ⋯ en Marcador, badge "WD"/"👁" en POS, motivo bajo el nombre

### Added — Admin de canchas CRUD + GPS por hoyo

- DB: `courses.created_by`; `course_holes.green_latitude`, `green_longitude`, `tee_latitude`, `tee_longitude`
- `PUT /courses/{id}`, soft `DELETE`, `PUT/POST /courses/{id}/holes` (batch + validación SI único + recálculo par_total)
- Ruta `/courses/[id]/edit` con tabs Detalles + Hoyos
- Botón "Capturar mi ubicación" con `navigator.geolocation` (enableHighAccuracy)
- Input "Pegar de Google Maps" — `parseLatLng` acepta `lat,lng`, URLs con `@lat,lng`, `?ll=`, `?q=`

### Added — GPS distance al pin en vivo

- Botón "GPS" en la barra del hoyo cuando hay coords del green
- `navigator.geolocation.watchPosition` con `enableHighAccuracy`
- Haversine → "X yds al pin" en verde grande + accuracy ± metros + punto pulsante
- Auto-cleanup al cambiar de hoyo / salir / tocar display
- Requiere HTTPS (golfbookvip.com ✅)

### Added — Stats personales, proyección y modo offline

- Mini-card 5 columnas: Eagles · Birdies · Pars · Bogeys · Dbl+
- Proyección de score final (stroke/stableford/skins): gross actual + par restante + ritmo
- Cola offline en `localStorage.pendingScores:{roundId}` con auto-sync al recuperar conexión
- Banners: rojo "Sin conexión · N en cola", amber "Sincronizando N score(s)"
- 4xx NO se reintentan (conflictos, validación); solo errores de red
- `beforeunload` y back-button interceptan si hay cambios sin guardar

### Added — Mejoras de captura

- Nombre del campo en franja superior uppercase tracking-widest
- Net Par junto al Par del hoyo cuando recibes strokes
- Botón Pickup / X (Net Double Bogey) por jugador — regla WHS
- Validación de score absurdo (>NDB+2 o <1) confirma antes de guardar
- Modal explicativo "¿qué es SI?" con ejemplo personalizado (usa course_handicap real)

### Changed — Visual

- Background del Play page: foto fija de campo de golf con lago (`/play-bg.jpg`) + velo `zinc-950/55`
- Header del hoyo en 3 columnas: izq=Par+SI · centro="HOYO N" 4xl emerald · der=yardaje+tee
- Footer con versión visible: "Desarrollado por AleaSystems · v1.0.0" en `emerald-400` (alto contraste)

### Changed — Stack

- CaddyAI migrado de Anthropic SDK a Google Gemini (`google-generativeai 0.8.3`)

### Fixed — Service Worker y cache

- `next.config.ts` envía `Cache-Control: no-cache, no-store` solo para `/sw.js` (Cloudflare cacheaba 4h)
- SW detecta nuevo waiting → `SKIP_WAITING` → `controllerchange` → recarga automática
- `pageshow` con `event.persisted` → `registration.update()` para BFCache
- `CACHE_NAME` bump v1→v2→v3

### Fixed — Flashes y parpadeos

- Loading state de Play usa la misma foto+overlay para evitar parpadeo oscuro
- `BackgroundProvider` global apunta a `/play-bg.jpg` (era `/golf-play.jpg`); eliminado `<div>` duplicado
- Course edit: `load` ya no depende de `lbl` recreado cada render (rompe loop infinito)
- Reset de `rowInputs` al cambiar de hoyo preserva filas dirty cuando entra WS event de otro jugador

### Fixed — Captura cruzada legacy

- Rondas sin tee_groups muestran selector "¿Para quién?" con groupMates derivados de `/players`
- Backend permite captura libre cuando ningún jugador tiene tee_group asignado

---

Para historial previo a 1.0.0, consultar `git log --until='2026-05-10'`.

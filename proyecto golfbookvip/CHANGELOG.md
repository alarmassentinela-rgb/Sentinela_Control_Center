# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado [Semantic Versioning](https://semver.org/lang/es/).

Cada release está respaldada por un tag git (`git checkout v1.0.0-golfbookvip` para volver a ese estado).

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

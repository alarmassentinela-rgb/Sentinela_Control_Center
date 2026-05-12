# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado [Semantic Versioning](https://semver.org/lang/es/).

Cada release está respaldada por un tag git (`git checkout v1.0.0-golfbookvip` para volver a ese estado).

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

# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado [Semantic Versioning](https://semver.org/lang/es/).

Cada release está respaldada por un tag git (`git checkout v1.0.0-golfbookvip` para volver a ese estado).

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

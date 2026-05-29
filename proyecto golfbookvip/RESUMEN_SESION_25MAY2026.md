# Resumen Sesión 25-may-2026 — GolfBookVIP

## Feature: Tope de Handicap por Ronda (`max_handicap`)

Cada ronda puede tener un tope opcional de course handicap. Jugadores con `course_handicap` mayor al tope son tratados como si tuvieran el tope, para efectos de cálculo de strokes recibidos por hoyo (WHS) → afecta `net_score` y `stableford_points`.

### Lógica

```
effective_ch = min(player.course_handicap, round.max_handicap or ∞)
strokes_received = WHS(effective_ch, hole.stroke_index)
net = gross - strokes_received
```

- `max_handicap = NULL` o `0` → sin tope (CH real del jugador)
- `max_handicap = 18` → jugadores con CH 19+ se topan a 18
- El tope se aplica **al capturar el score** (se persiste el net topado)
- Scores **ya capturados** ANTES de cambiar el tope NO se recalculan automáticamente

### Cambios

| Capa | Archivo | Cambio |
|---|---|---|
| DB | `rounds` | `ALTER TABLE rounds ADD COLUMN max_handicap INTEGER NULL` |
| Model | `app/models/round.py` | Campo `max_handicap: Mapped[Optional[int]]` |
| Schema | `app/schemas/round.py` | `RoundCreate`, `RoundUpdate`, `RoundOut` ← `max_handicap: Optional[int]` |
| Scoring | `app/services/scoring.py` | Helper `effective_handicap(ch, cap)`. `apply_score_to_model(...)` recibe `max_handicap` opcional y capa antes de `strokes_received` |
| API | `app/api/v1/rounds.py` | 3 call-sites de `apply_score_to_model` pasan `round_.max_handicap` (submit score, fix conflict, seed mock) |
| Frontend `/rounds/new` | `frontend/src/app/[locale]/rounds/new/page.tsx` | Input numérico 0-54 con hint dinámico; envía `null` si es 0 |
| Frontend `/rounds/[id]` | `frontend/src/app/[locale]/rounds/[id]/page.tsx` | Type `Round.max_handicap`, edit form input + nota "scores ya capturados no se recalculan", badge ámbar "Tope HCP N" en header |

### Por qué se aplicó solo al cálculo y NO se recomputaron scores viejos

- `Score.net_score` es columna persistida, no computed
- Recompute retroactivo es operación destructiva — preferí dejarlo manual/explícito por seguridad
- Si en el futuro se necesita: query `UPDATE scores ...` o endpoint admin que recorra `round.scores` y rerun `apply_score_to_model`

### Balances.py no requirió cambios

Todas las apuestas net-based (`skins_use_net`, `nassau`, etc.) leen `s.net_score` ya persistido, que viene topado desde `apply_score_to_model`. El `course_handicap` que aparece en balances.py:401 es solo display.

---

## Incidente: Service Worker envenenado tras rebuild ("Sin conexión")

### Síntoma

Después de hacer `docker compose build frontend` + restart, los usuarios con la PWA o pestaña previa abierta veían pantalla "Sin conexión" (offline.html del SW).

### Causa raíz

El SW `golfbookvip-v3` (en `/public/sw.js`) usa estrategia **Cache First para `/_next/static/*`**. Cuando el rebuild cambia los hashes de los chunks JS:

1. El SW viejo tiene el HTML pre-rebuild cacheado (apunta a chunks viejos)
2. El SW devuelve esa HTML stale (via network-first que cachea respuestas)
3. Browser pide chunks **viejos** que ya no existen en server → 404
4. Fallback del SW: offline.html

`clients.claim()` y `skipWaiting` no ayudan porque la pestaña activa mantiene controlling el SW viejo hasta que se cierren TODAS las pestañas del origen.

### Solución aplicada

`/public/sw.js` reemplazado por un **kill switch v5**:

```js
const CACHE_NAME = 'golfbookvip-v5-killer'

self.addEventListener('install', () => self.skipWaiting())

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys()
    await Promise.all(keys.map((key) => caches.delete(key)))
    await self.clients.claim()
    // Auto-reload de todas las pestañas controladas
    const clients = await self.clients.matchAll({ type: 'window' })
    clients.forEach((c) => c.navigate(c.url))
  })())
})
// NO fetch handler → browser usa network directo
```

Tras recargar la pestaña, el browser detecta el SW nuevo, lo activa, borra TODOS los caches y se auto-recarga.

### Deploy del SW

`sw.js` vive en `frontend/public/` pero el container usa el copy del build (en `/app/public/`). Para que el cambio surta efecto sin rebuild completo:

```bash
rsync sw.js → server:/opt/golfbookvip/frontend/public/sw.js
ssh sudo docker cp /opt/golfbookvip/frontend/public/sw.js golfbookvip_frontend:/app/public/sw.js
ssh docker restart golfbookvip_frontend
```

### Lección para futuros deploys

**Cada rebuild de frontend debe bumpear `CACHE_NAME` en `sw.js`** — si no, los usuarios con la PWA activa pueden ver el offline page hasta que cierren todas las pestañas.

Opciones más limpias para el futuro:
- Auto-bump en el Dockerfile build (`sed -i "s/golfbookvip-v.*/golfbookvip-${BUILD_ID}/" public/sw.js`)
- Cambiar estrategia a **Network First para `/_next/static/`** (descarta cache vieja siempre que haya red)
- Quitar el SW para `/_next/static/` (que el browser maneje caching nativo)
- Después de validar que el kill-switch limpió las caches viejas en producción, restaurar el SW con caching útil (offline.html, pre-cache de iconos)

---

## Deploy ejecutado

1. Backend: `rsync` + `docker restart golfbookvip_api` → app levantó sin errores
2. Frontend: `docker compose build frontend` → genera imagen nueva
3. Extracción de `.next` del image vía `sudo docker create --name gbvip_tmp golfbookvip-frontend:latest` + `docker cp gbvip_tmp:/app/.next /opt/golfbookvip/frontend/`
4. `docker compose up -d --force-recreate frontend`
5. SW killer copiado al container y restart

Smoke tests: `/es`, `/en`, `/es/rounds/new`, `/es/dashboard`, `/es/rounds` → todos 200.

## Pendientes para próxima sesión

- ¿Restaurar SW con caching útil pero estrategia revisada? (decidir si vale la pena vs. el dolor que causó)
- Si se restaura: agregar bump automático de `CACHE_NAME` al pipeline de build
- Considerar agregar botón "Recomputar scores" en edit form para casos donde se cambia `max_handicap` post-facto
- Validar formato Florida con tope de handicap (no se probó)

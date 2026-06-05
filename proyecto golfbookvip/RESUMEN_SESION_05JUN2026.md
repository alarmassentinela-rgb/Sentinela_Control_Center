# Resumen Sesión 4–5 jun 2026 — GolfBookVIP

Tres entregas, todas **desplegadas a producción y pusheadas a `origin/main`**. Reportadas por Enrique tras jugar golf con la app.

| Versión | Tipo | Qué |
|---|---|---|
| **1.23.1** | fix | Jugadores agregados manualmente sí aparecen para capturar score |
| **1.24.0** | feat | Modo Sol — tema claro de alto contraste para leer en el campo |
| **1.24.1** | fix | El score por defecto (par) se guarda aunque no se toque |

---

## 1.23.1 — Jugadores agregados a mano no aparecían para capturar score

**Síntoma (Enrique):** agregó 2 jugadores manualmente + 1 por la liga; al iniciar la jugada solo aparecían él (creador) y el de la liga para capturar score; los 2 manuales no.

**Causa raíz:** `invite_player` (`app/api/v1/rounds.py`) guardaba al jugador con `status="invited"`, y **no existe ningún endpoint** para pasar de "invited" a "confirmed". Toda la captura de score filtra solo `confirmed`/`playing`:
- `start_round`, `submit_score`, pantalla `/play` (`play/page.tsx:690`), y la finalización.
- El creador queda `confirmed` al crear; quien entra por la liga queda `confirmed` al unirse → esos dos sí aparecían.

**Fix:** agregar manualmente ahora **confirma al jugador de una vez** (`status="confirmed"` + `confirmed_at`), igual que el join por liga.

**Deploy backend:** rsync `app/api/v1/rounds.py` → server + `docker compose restart api`. Verificado: `status="confirmed"` presente en el contenedor (línea 405), API healthy.

⚠️ Pendiente menor (si aplica): la jugada de prueba previa pudo dejar jugadores en `invited` en la BD; el fix aplica a jugadas nuevas. Si hace falta recuperar una ronda vieja, cambiar esos `round_players.status` a `confirmed` a mano.

---

## 1.24.0 — Modo Sol (tema claro de alto contraste)

**Necesidad (Enrique):** bajo el sol directo en el campo el tema oscuro no se lee.

**Contexto técnico:** la app NO tenía tema claro/oscuro. El modo oscuro está hardcodeado en ~50 archivos (~3,764 usos de `zinc-950/900/800`, **707 `text-white`**) + un `BackgroundProvider` que pinta fotos de golf con velo oscuro y tarjetas de vidrio oscuro. Convertir todo a claro = enorme y frágil.

**Decisión de Enrique:** botón toggle "Modo Sol" (no tema permanente). Conserva el oscuro para uso bajo techo.

**Implementación (sin tocar las ~50 pantallas):**
- `frontend/src/components/SunModeToggle.tsx` (NUEVO): botón flotante ☀️/🌙 abajo-izquierda. Pone `data-theme="sun"` en `<html>`, persiste en `localStorage` (`gbv-sun-mode`).
- `frontend/src/app/globals.css`: capa de override `html[data-theme="sun"]` → sábana blanca que tapa las fotos (body::before z-index -5), fondos zinc→claros con jerarquía, header/tarjetas glass→blancas, textos claros (white/zinc-100..500)→oscuros, bordes→gris claro, acentos (emerald/red/amber/yellow/blue/orange en tonos 200–500)→tono oscuro legible sobre blanco, inputs con texto oscuro.
- `frontend/src/app/[locale]/layout.tsx`: `<Script id="gbv-sun-mode-init" strategy="beforeInteractive">` anti-flash + montaje del botón.

Verificado: el `.css` servido contiene las reglas `data-theme="sun"`.

---

## 1.24.1 — El score por defecto (par) no se guardaba si no se tocaba

**Sospecha (Enrique):** "si no capturo el número que ya está por default (el par del hoyo), ¿sí se guarda? Revísalo en todas las modalidades."

**Confirmado: NO se guardaba.** En `play/page.tsx`:
- El contador de cada jugador arranca en `hole.par` con `dirty=false` (init en `useEffect`, ~línea 813).
- `submitScore` **solo enviaba filas `dirty`** (tocadas con +/−, pickup o putts). Un hoyo dejado en el par sin tocar → no se enviaba → **hueco**. El botón hasta se etiquetaba "Siguiente hoyo" y avanzaba.

**Aplica a TODAS las modalidades:** la pantalla de captura y `submitScore` son **comunes** a stroke/match/florida/gran premio/skins. Los formatos solo cambian las vistas de resultados read-only (`match-scores`, `florida-scores`, `leaderboard`).

**Seguridad del fix (backend):** reenviar un valor idéntico NO genera conflicto — el backend solo marca conflicto si **otra persona** mete un valor **distinto** (`submit_score` en `rounds.py`).

**Fix (`submitScore`):** al guardar el hoyo, también persiste el valor mostrado (default = par) de cualquier jugador que aún no tenga score. Reglas:
- Fila tocada (`dirty`) → siempre se guarda.
- Fila ya guardada → no se reenvía.
- Fila sin tocar y sin score → se guarda el default **si** es la propia o **si** soy el capturista designado/creador (`authoritative`). En modo legacy sin capturista, cada quien guarda solo el suyo.
- Botón: "Guardar hoyo" (verde) cuando hay algo por guardar (incluidos defaults sin guardar); "Siguiente hoyo" solo cuando todo el grupo ya tiene score.

---

## Receta de deploy del frontend (confirmada esta sesión)

El `.next`/`public` del server (`/opt/golfbookvip/frontend/`) son **bind-mounts root-owned** → `rsync` como `egarza` falla (chgrp/mkdir permission denied). El server corre `npm run start` leyendo ese `.next`. Flujo que funciona:

```bash
# local
cd frontend && npm run build
cd .next && tar czf /tmp/gbv_next.tgz --exclude=./cache --exclude=./dev .
scp /tmp/gbv_next.tgz 192.168.3.2:/tmp/
# server (egarza tiene acceso a docker)
ssh 192.168.3.2
  mkdir -p /tmp/gbv_next && tar xzf /tmp/gbv_next.tgz -C /tmp/gbv_next
  docker exec golfbookvip_frontend sh -c 'rm -rf /app/.next/* /app/.next/.[!.]*; mkdir -p /app/.next'
  docker cp /tmp/gbv_next/. golfbookvip_frontend:/app/.next/   # escribe como root vía bind-mount
  cd /opt/golfbookvip && docker compose restart frontend
```

Verificar: `BUILD_ID` local == server, HTTP 200 en `/es/dashboard` y `/es/rounds/.../play`.

- **SSH:** `Host 192.168.3.2` (config: Port 2222, user `egarza`, key `id_rsa_sentinela`). `ssh root@` falla.
- **Backend (Python):** más simple — `app/` es bind-mount normal: rsync + `docker compose restart api`.

---

## Estado final

- Repo en **v1.24.1**, todo commiteado y pusheado a `origin/main` (último: jugadores manual fix → Modo Sol → par default).
- Contenedores `golfbookvip_api` y `golfbookvip_frontend` healthy/up en producción.

### Pendiente de validación por Enrique (en el campo / próxima jugada)
1. Agregar jugadores a mano y confirmar que aparecen para capturar score.
2. Probar el botón **Modo Sol** bajo el sol; ajustar tono/posición/tamaño si hace falta.
3. Dejar un hoyo en el par sin tocar, **Guardar hoyo**, y verificar que el par quedó registrado en el marcador.

Opción ofrecida (no implementada): marcar visualmente los hoyos aún sin capturar para no saltarse ninguno.

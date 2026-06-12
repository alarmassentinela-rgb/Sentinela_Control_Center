# Resumen de sesión — 12 de junio 2026

**Proyecto:** GolfBookVIP (golfbookvip.com) — app standalone, NO módulo Odoo.
**Arco de la sesión:** v1.25.0 → **v1.29.0**. Todo desplegado a producción, commiteado y pusheado. Repo y prod alineados; el footer de la UI vuelve a mostrar la versión real (se cerró el desfase que venía desde 1.23.0).

> Nota: el trabajo se hizo de corrido; las fechas internas del CHANGELOG quedaron en 10–11 jun (cuando se cortó cada release). El cierre formal es hoy.

---

## 1. Guías de usuario en PDF — v1.25.0

- Generador `proyecto golfbookvip/docs/manual/build_pdf.py` (NUEVO): convierte los 4 `.md` de `docs/manual/` (Jugador + Organizador × ES/EN) a PDF con **PyMuPDF** (no hay pandoc/weasyprint en el WSL; pymupdf sí, mismo motor que CFDI). Portada de marca, header/footer por página, tablas/notas/listas estilizadas. Regenerar: `python3 docs/manual/build_pdf.py`.
- Los 4 PDFs servidos en `frontend/public/guides/`; botón "Descargar guía en PDF" en `/ayuda` (según pestaña Jugador/Organizador + idioma).
- **Verificado:** los 4 PDFs por HTTPS → 200 `application/pdf`; `/ayuda` 200.

## 2. Balanceo de equipos — v1.25.1 y v1.25.2

- **v1.25.1** — Snake draft: reemplazó el interleave por módulo (`idx % N`) por reparto serpentina por tiers. Equipos mucho más parejos (spread 0 en cupos divisibles vs 12/8/4).
- **v1.25.2** — Cupos NO divisibles parejos. Reemplazó el snake-por-tier por `_balanced_assignment(rps, num_teams)` en `app/api/v1/rounds.py`:
  - `ceil(M/N)` grupos de salida de tamaño parejo (**10/4 → 4·3·3**, no 4·4·2).
  - Tallas de equipo ≤1 y promedio de HCP parejo (greedy: equipos menos cargados toman el grupo, peor HCP al equipo más liviano).
  - Conserva un jugador por equipo en cada grupo.
  - Usado por `/teams/generate` (manual) y `/auto-setup` (Gran Premio).
- **Verificado:** 40 000 cupos aleatorios (N=2..12, M=N..48) sin romper invariantes (distinct por grupo, tallas equipo ≤1, tallas grupo ≤1); test corrido sobre la función REAL extraída del archivo.

## 3. Grupos privados — de esqueleto a completos (v1.26.0 → v1.29.0)

Diagnóstico inicial: los grupos privados eran un CRUD social **sin payoff** (crear/invitar/listar miembros, pero nada que hacer dentro). Se cablearon 4 features:

- **v1.26.0 — Rondas de grupo.** Cableó el `Round.group_id` que ya existía pero `create_round` ignoraba (en realidad lo guardaba vía `model_dump`, solo faltaba validar membresía → ahora 403 si no eres miembro). Nuevo `GET /groups/{id}/rounds`. Sección "Rondas del grupo" + botón "Nueva ronda" en `/groups/[id]`; `/rounds/new` lee `?group_id/&group_name` y muestra banner.
- **v1.27.0 — Leaderboard del grupo.** `GET /groups/{id}/leaderboard`: rankea miembros sobre las rondas FINALIZADAS por **victorias (1.º en net) → handicap → mejor net**. Página `/groups/[id]/leaderboard` (medallas top-3). Sin rondas ordena por handicap.
- **v1.28.0 — Muro de posts.** Activó el modelo `Post`/`PostComment`/`Reaction` (tablas ya existían en la DB, sin usar). Endpoints `/groups/{id}/posts` (listar/publicar/borrar/`/react` toggle like/`/comments`), manteniendo contadores. Página `/groups/[id]/wall` (composer, like optimista, hilo de comentarios). MVP texto+like.
- **v1.29.0 — Fotos en los posts** (hasta 4/post). Infra de subida NUEVA: `POST /api/v1/uploads/image` (`app/api/v1/uploads.py`, Pillow: EXIF-transpose + resize ≤1600 + thumb ≤400, JPEG, máx 10MB) → `MEDIA_ROOT/posts/`. `main.py` monta `StaticFiles` en `/media`. `PostCreate` acepta `media[]` (valida prefijo `MEDIA_URL`) → filas `PostMedia`. Composer con botón "Foto" + previews; render en grid en cada post.
- **Verificado:** endpoints nuevos → 403 sin auth (registrados); pipeline de fotos probado end-to-end en prod (imagen 2400×1800 → 11KB + thumb 1KB, servida por HTTPS `image/jpeg`); todos los builds con BUILD_ID local = server.

## Deploy (recordatorio de la trampa)

- **Backend** (`app:/app/app` montado): rsync `app/...` + `docker compose restart api`.
- **Frontend** (`.next`/`public` bind-mounts root-owned): build local → tar → scp → `docker cp` al container `golfbookvip_frontend` → restart. **Lección de proceso:** bumpear `version.ts` ANTES del build para no rebuildeart dos veces (al principio de la sesión se rebuildó de más).

---

## Pendientes para la próxima sesión

1. ⚠️ **Respaldar `media_data`** — las fotos del muro viven en el volumen Docker `media_data` del api (persisten en restart/rebuild) pero **NO están en la estrategia de respaldo** (solo DB+addons). Respaldar el volumen o mover a object storage.
2. **Probar end-to-end en navegador con sesión real** lo de hoy (rondas de grupo, leaderboard, muro, subir fotos) — Claude verificó infra/endpoints pero no el flujo con login.
3. **Reacciones múltiples** en el muro (la DB ya permite `like/fire/clap/laugh/sad`; hoy solo 👍).
4. **Avatares de usuario** reusando la infra de `/uploads/image` (User/Group ya tienen `avatar_url` sin endpoint).
5. Pendientes viejos de golfbookvip: **Guía del Club** (PDF) y **recálculo masivo de handicaps**.

## Versión / commits

- Prod y repo en **v1.29.0**. Tags `v1.25.0` … `v1.29.0-golfbookvip` pusheados.
- Último commit de feature: `fbbb3c1` (fotos en posts).

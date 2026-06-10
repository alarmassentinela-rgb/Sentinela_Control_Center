---
name: cierre-sesion
description: >-
  Cierra la sesión de trabajo: redacta el RESUMEN_SESION_<FECHA>.md del día,
  actualiza la memoria persistente (MEMORY.md + archivos de memoria), y crea el
  commit `docs: resumen sesión...`. Úsalo cuando Enrique diga "cierra la sesión",
  "documenta lo de hoy", "guarda lo que hicimos" o al terminar la jornada.
---

# Cierre de sesión

Cada jornada termina con tres artefactos: un resumen en el repo, la memoria
actualizada, y un commit. Esta skill produce los tres de forma consistente.

## 1. Reconstruir qué pasó hoy
- Revisar `git log --oneline` desde el último `docs: resumen` para ver releases/cambios.
- Repasar la conversación: decisiones, fixes, incidentes, pendientes que quedaron.
- Si hubo cambios de routers/infra, anotar qué se tocó y el rollback.

## 2. Redactar `RESUMEN_SESION_<DDMMMAAAA>.md`
Nombre como los previos: `RESUMEN_SESION_09JUN2026.md` (mayúsculas, mes en español 3 letras).
Estructura típica:
- Título + fecha.
- Secciones por área (WISP/red, Suscripciones, GPS, Monitoring, etc.).
- Por cada cosa: qué se hizo, versión/commit, verificación real, y rollback si aplica.
- **Pendientes** numerados para la próxima sesión.

## 3. Actualizar memoria persistente
Memoria en `/home/egarza/.claude/projects/-mnt-c-Users-dell-DellCli/memory/`.
- Si la sesión generó algo duradero (decisión, arquitectura, incidente con causa raíz,
  procedimiento nuevo) → crear/actualizar un archivo de memoria con su frontmatter
  (`type: project|reference|feedback|user`) y `**Why:**` / `**How to apply:**`.
- Convertir fechas relativas a absolutas.
- Agregar/editar la línea-puntero en `MEMORY.md` (una línea, con gancho).
- Preferir **actualizar** un archivo existente antes que duplicar. Enlazar con `[[name]]`.
- NO guardar lo que el repo/git ya registra (estructura de código, historial).

## 4. Commit
Convención del historial: `docs: resumen sesión <fecha> (...)` — descripción corta
de lo más relevante entre paréntesis. Ejemplos reales:
```
docs: completa resumen 7-jun (validar navegación + candado anti-duplicado + ...)
docs: resumen sesión 7-jun (PCC balanceo investigación + Argus cerrado + handoff laptop)
```
```bash
git add RESUMEN_SESION_<FECHA>.md SENTINELA_PROJECT_CENTER.md
git commit -m "docs: resumen sesión <fecha> (<lo relevante>)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push origin main
```
La memoria (`~/.claude/.../memory/`) NO se commitea al repo del proyecto (vive aparte).

## 5. Reportar
Listar: qué resumen se creó, qué memorias se tocaron, el hash del commit, y los
pendientes que quedaron abiertos para retomar.

## Notas
- Si en la sesión quedó algo a medio desplegar, decirlo explícito en los pendientes.
- No inventar verificaciones: si algo no se probó, escribirlo como "sin validar".

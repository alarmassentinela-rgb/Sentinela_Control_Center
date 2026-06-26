# ADR-0005 — Sesiones cortas: access revocable + refresh rotativo (reuse)

**Estado:** Aceptada (26-jun-2026)

## Contexto
Se requieren sesiones seguras de vida corta, revocables de inmediato, sin credenciales permanentes.

## Decisión
- **Access JWT corto** (~15 min) **revocable**: cada request valida en DB que la sesión exista y no esté revocada.
- **Refresh token** opaco, **rotativo de un solo uso** (claim atómico) con **detección de reuse** → revoca toda la familia (mitiga robo).
- Cierre individual y global; revocación automática al cambiar credenciales críticas.

## Consecuencias
- (+) Revocación inmediata real (no se espera a que expire el JWT).
- (+) Robo de refresh detectable y contenido.
- (−) Una consulta a DB por request autenticado (aceptable; índice en `access_jti`).

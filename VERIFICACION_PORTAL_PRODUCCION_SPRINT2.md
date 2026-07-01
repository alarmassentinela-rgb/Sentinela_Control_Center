# Verificación de Producción — `portal.sentinela.mx` (Sprint 2)

**Fecha:** 2026-07-01 · **Naturaleza:** verificación **read-only** del ingreso al Portal de Producción. **No se modificó ninguna configuración** (NPM/Cloudflare/DNS/TLS) ni Stripe.
**Objetivo:** confirmar que la SPA de Producción puede publicarse en `portal.sentinela.mx` e identificar bloqueos antes de la ventana de liberación del Sprint 2.

---

## Resultado por punto
| # | Punto | Estado | Evidencia |
|---|---|:--:|---|
| 1 | **DNS** | ✅ | `portal.sentinela.mx` resuelve por Cloudflare (mismas IPs que `api.sentinela.mx`). |
| 2 | **Cloudflare** | ✅ | Proxied (`server: cloudflare`, `cf-ray`); enruta al origen. |
| 3 | **NPM (proxy host #9)** | ✅ | `server_name portal.sentinela.mx` → `192.168.3.2:3090` (`coc-web-prod`, SPA de Producción). Referencia: #8 `api.sentinela.mx` → `:8400` (gateway). |
| 4 | **TLS** | ✅ | Cert **wildcard `*.sentinela.mx`** (Let's Encrypt), vigente **29-jun → 27-sep 2026**. |
| 5 | **SPA servida** | ✅ | `x-powered-by: Next.js`; rutas reales `/login`, `/dashboard`, `/facturacion` = **200**. |
| 6 | **API base de la SPA** | ✅ | La SPA prod apunta a `https://api.sentinela.mx` (gateway prod). |

## Aclaración del supuesto "404"
En un sondeo inicial se probó `https://portal.sentinela.mx/health` y devolvió **404**. Esto **NO era un problema del Portal**: `/health` **no es una ruta de la SPA** (Next.js responde 404 para rutas inexistentes). Las **rutas reales** del portal (`/login`, `/dashboard`, `/facturacion`) responden **200**. El Portal estaba —y está— correctamente publicado.

## Conclusión
**El ingreso al Portal está completo y operativo.** No falta ningún ajuste de infraestructura (DNS/Cloudflare/NPM/TLS). Hoy sirve la SPA del **Sprint 1** (consulta).

## Implicación para la liberación del Sprint 2
- El ingreso es **transparente al despliegue**: al publicar la **SPA 0.6.0** (reemplazando la imagen de `coc-web-prod` en `:3090`), `portal.sentinela.mx` servirá automáticamente la nueva SPA **sin tocar** NPM/Cloudflare/DNS/TLS.
- **Prerrequisito de Portal: RESUELTO / sin bloqueos.**

## Nota
Cloudflare está *proxied* delante de `api.sentinela.mx`; los webhooks **LIVE** de Stripe (2ª ventana) llegarán por ese ingreso (ya responde 200). No requiere cambios en el Portal.

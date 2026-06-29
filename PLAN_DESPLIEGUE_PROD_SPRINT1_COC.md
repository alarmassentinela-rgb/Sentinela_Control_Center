# Plan de Despliegue a Producción — Sprint 1 (Portal COC)

**Estado:** BORRADOR para tu revisión. **No ejecutar sin tu autorización explícita.**
**Fecha:** 2026-06-29 · **Base:** UAT STAGING **APROBADA** (`REPORTE_UAT_SPRINT1_COC.md`) · paridad STAGING↔repo verificada.
**Referencia previa:** `DEPLOY_RUNBOOK_COC_RC1.md` (cubrió RC1/identidad). Este plan cubre el **incremento Sprint 1**.

---

## 0. Estado real de Producción (verificado hoy)

| Componente | Estado en PROD | ¿Acción requerida? |
|---|---|---|
| **Odoo `sentinela_api`** (V18) | `installed 18.0.0.2.0` y **rutas Sprint 1 YA VIVAS** (`/v1/services`, `/v1/billing/*`, `/v1/me` → 303, no 404). Código en disco = repo (md5 ✓). | **NINGUNA** (solo verificar). |
| **Gateway (BFF)** | **`0.2.0`** (solo RC1/identidad). Sin `portal.py`. Apunta a Odoo prod `:8070`, OTP evoapi `SentinelaWA`, DB postgres `gateway-db`. | **SÍ — actualizar a `0.3.2`.** |
| **SPA** (`portal.sentinela.mx`) | **No existe en prod.** | **SÍ — construir y publicar.** |
| **Ingreso público** | `api.sentinela.mx` / `portal.sentinela.mx` **no resuelven**. Gateway solo en LAN `:8400`. | **SÍ — exponer (Cloudflare Tunnel + NPM).** |

> **Conclusión:** la promoción del Sprint 1 = **(A) actualizar el Gateway** + **(B) publicar la SPA** + **(C) abrir el ingreso público**. El backend Odoo **ya está listo**.

---

## 1. Precondiciones (checklist antes de abrir la ventana)

- [ ] **UAT STAGING aprobada** ✅ (este reporte) + observación cosmética aprobada ✅.
- [ ] **Commit/release del código validado** (hoy el repo tiene 1 cambio sin commitear: el pie del Login). Antes del deploy:
  - `release-modulo` no aplica al SPA; commitear manualmente `feat(web): pie institucional en Login (cosmético UAT)` + bump `web` a `0.4.1` + tag de respaldo `coc-web-v0.4.1`.
  - El árbol debe quedar **limpio** (`git status` sin pendientes) y **pusheado** a GitHub.
- [ ] **Confirmar paridad** final repo↔STAGING (gateway 0.3.2 md5 ✓, SPA login md5 ✓, `sentinela_api` md5 ✓).
- [ ] **Secretos de producción presentes** (no en repo): `/opt/sentinela_coc/.env` con `COC_JWT_SECRET`, `COC_COC_SHARED_SECRET` (= `sentinela_api.gateway_shared_secret` de V18), `COC_WA_API_KEY`, DB del gateway. **Verificar que `COC_CORS_ORIGINS` incluya `https://portal.sentinela.mx`** (agregar si falta).
- [ ] **EvoApi `SentinelaWA` conectada** (login real OTP) — `GET /v1/providers/health` → open.
- [ ] **DNS/Túnel listos**: registros `api.sentinela.mx` y `portal.sentinela.mx` en Cloudflare + ruta de Cloudflare Tunnel + proxy hosts en NPM (puede prepararse fuera de ventana, en modo "no público" hasta el corte).
- [ ] **Decisión de exposición**: ¿lanzamiento abierto a clientes, o primero **acceso restringido** (LAN / lista corta) para piloto? (Recomendado: piloto breve antes de difundir.)
- [ ] **Ventana acordada** + responsable disponible para verificación y eventual rollback.

## 2. Respaldo (antes de tocar prod)

- [ ] **DB Gateway (postgres `coc_gateway`)**: dump del volumen `portal_identity`/sesiones.
  `docker exec gateway-gateway-db-1 pg_dump -U coc coc_gateway | gzip > /home/egarza/backups/coc_gateway_$(fecha).sql.gz`
- [ ] **Imagen del gateway actual (rollback inmediato)**: `docker tag coc-gateway:dev coc-gateway:rollback-0.2.0` (o anotar el digest vigente).
- [ ] **`.env` de prod**: copia con fecha (`cp /opt/sentinela_coc/.env /opt/sentinela_coc/.env.bak_<fecha>`).
- [ ] **Odoo V18**: NO se modifica (sin `-u`); el respaldo regular (DB cada 8h + addons) cubre cualquier contingencia. No se requiere respaldo extra para este deploy.
- [ ] **Código**: ya en GitHub (precondición §1) — rollback por tag.

## 3. Orden exacto del despliegue

### Componente A — Gateway 0.2.0 → 0.3.2 (núcleo del incremento)
1. `rsync` del repo al server (el server NO es git tree):
   `rsync -az -e "ssh -p 2222" --exclude='__pycache__' --exclude='.env' sentinela_coc/gateway/ 192.168.3.2:/opt/sentinela_coc/gateway/`
2. (Si falta) editar `/opt/sentinela_coc/.env`: `COC_CORS_ORIGINS=https://portal.sentinela.mx`.
3. Reconstruir y recrear **solo** el gateway (la DB postgres persiste):
   `cd /opt/sentinela_coc/gateway && docker compose up -d --build`
4. Esperar readiness: `GET http://192.168.3.2:8400/health` → `version 0.3.2`.

### Componente B — SPA de producción
5. `rsync` del web (excluyendo artefactos): a `/opt/sentinela_coc/web/` (ya sincronizado; re-confirmar tras el commit).
6. Construir imagen **apuntando a la API pública**:
   `docker build --build-arg NEXT_PUBLIC_API_BASE=https://api.sentinela.mx -t coc-web:prod /opt/sentinela_coc/web`
7. Levantar contenedor de prod (puerto interno dedicado, p. ej. `3090:3000`, `--restart unless-stopped`):
   `docker run -d --name coc-web-prod --restart unless-stopped -p 3090:3000 coc-web:prod`
8. Verificar local: `GET http://192.168.3.2:3090/login` → 200 (con pie institucional).

### Componente C — Ingreso público (Cloudflare Tunnel + NPM)
9. **NPM**: proxy host `api.sentinela.mx` → `http://127.0.0.1:8400` (gateway) y `portal.sentinela.mx` → `http://127.0.0.1:3090` (SPA), con TLS (Let's Encrypt) y **WebSocket off** (no se usa).
10. **Cloudflare Tunnel**: rutas para ambos hostnames; DNS proxied (naranja).
11. **Odoo `/coc/internal/*` permanece SOLO LAN** (no exponer). Confirmar `sentinela_api.coc_internal_allowed_cidrs` restringido a la red del gateway en V18 (hoy en STAGING está `0.0.0.0/0`; en **PROD debe fijarse** a la subred del gateway).

> **Orden recomendado:** A (gateway) → verificar → B (SPA) → verificar local → C (ingreso público) → smoke público. Cada componente se valida antes del siguiente.

## 4. Verificaciones posteriores al despliegue (LAN, antes de abrir público)

- [ ] `GET :8400/health` → `0.3.2`; `GET :8400/v1/config/theme` → branding Sentinela (200).
- [ ] `GET :8400/openapi.json` lista las rutas Sprint 1 (`/v1/services`, `/v1/billing/*`, `/v1/dashboard`, `/v1/me`).
- [ ] Gateway → Odoo prod: `:8400/v1/dashboard` con una sesión real → 200 (proxya a `:8070`).
- [ ] `:3090/login` → 200 con pie institucional; consola del navegador limpia.
- [ ] `GET :8400/metrics`, `/v1/providers/health` (EvoApi open), logs estructurados con `request_id`.
- [ ] No-regresión RC1: `/v1/auth/otp/request` responde (neutro) y `/v1/sessions` protegido.

## 5. Smoke Test en Producción (extremo a extremo, datos reales)

Ejecutar con un **cliente de prueba real** (número WhatsApp del operador → su partner):
1. **Login OTP real**: `portal.sentinela.mx` → ingresar teléfono → recibir OTP por WhatsApp → verificar → entra a Dashboard. (mide < ~2 s envío OTP).
2. **Dashboard**: Estado de Tranquilidad + saldo + servicios coherentes con ese cliente.
3. **Mis Servicios**: lista + detalle.
4. **Facturación**: resumen + lista + **descargar 1 PDF (CFDI)** y, si aplica, **1 XML** → válidos.
5. **Aislamiento**: intentar abrir por URL una factura ajena → error amigable (no fuga).
6. **Sesión**: cerrar/expirar → `/login?expired=1` con banner.
7. **Responsive**: abrir en un teléfono real (móvil) y en escritorio.
8. **Consola** del navegador sin errores; `X-Request-Id` presente.

✅ Criterio de éxito del smoke: pasos 1–6 correctos + consola limpia + observabilidad activa.

## 6. Criterios de Rollback

Disparar rollback si, tras el deploy, ocurre cualquiera:
- Gateway no levanta `0.3.2` / `/health` falla / errores 5xx sostenidos.
- Login OTP real no completa (resolve→sesión) o EvoApi caído sin recuperación.
- Aislamiento roto (un cliente ve datos de otro) → **rollback inmediato + incidente**.
- CFDI PDF/XML no descargan (502 persistente) o caché/latencia inaceptable.
- Regresión en RC1 (identidad/sesiones).

**Procedimiento de rollback (por componente, bajo riesgo, stateless):**
| Componente | Rollback | Datos |
|---|---|---|
| Gateway | `docker compose` a imagen previa (`coc-gateway:rollback-0.2.0`) y `up -d` | DB gateway intacta (persistente) |
| SPA | `docker rm -f coc-web-prod` (la SPA aún no es crítica si se aborta el lanzamiento) | sin datos |
| Ingreso público | Deshabilitar proxy hosts NPM / ruta del túnel (vuelve a LAN) | sin datos |
| Odoo V18 | **N/A** (no se tocó) | — |
- Caso extremo: restaurar `coc_gateway_<fecha>.sql.gz`. Odoo no requiere restauración (no se modificó).

## 7. Tiempo estimado de la ventana

| Fase | Estimado |
|---|---|
| Precondiciones + respaldos | 15–20 min |
| A. Gateway 0.3.2 (build+recreate+verif.) | 10–15 min |
| B. SPA build + contenedor | 10–15 min |
| C. Ingreso público (NPM + túnel + DNS/TLS) | 20–40 min (mayor variabilidad: propagación/cert) |
| Smoke en producción | 15–20 min |
| **Total ventana** | **~75–110 min** (≈ 1.5–2 h con margen) |

> Si el ingreso público (C) se prepara **fuera de ventana** (DNS/túnel/NPM ya listos en modo no-difundido), la ventana de corte se reduce a **~45–60 min** (A+B+smoke).

## 8. Post-deploy (cierre)

- [ ] Programar cron de alertas (`sentinela_coc/infra/alerts/`) → Telegram (pendiente RC1).
- [ ] Fijar `sentinela_api.coc_internal_allowed_cidrs` a la subred del gateway en V18.
- [ ] `RELEASE_NOTES` del Sprint 1 + tag de despliegue (`coc-sprint1-v1.0.0`).
- [ ] Actualizar memoria del proyecto (Portal COC: Sprint 1 en PROD).
- [ ] **Recién entonces**: habilitar el arranque de **Sprint 2 (S2-000)**.

---

**No se ejecuta ningún paso hasta tu autorización.** Revísalo y, al aprobarlo, emite la orden de promoción a Producción del Sprint 1.

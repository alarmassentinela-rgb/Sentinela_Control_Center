# Pre-Flight Checklist — STAGING Sprint 2 (Cobranza)

**Fecha:** 2026-06-30 · **Objeto:** preparar el despliegue del RC `coc-v1.2.0-rc1` a STAGING (Etapa 3 del `PLAN_RC1_SPRINT2_COBRANZA.md`).
**Naturaleza:** inspección **read-only** del entorno. **No se desplegó ni modificó nada.**
**Servidor:** `192.168.3.2` (host `AleaSystems`, Ubuntu 24.04.4 LTS, kernel 6.8.0-124).
**Leyenda:** ✅ OK · ⚠ Advertencia · ❌ Bloqueante.

---

## Resultado por punto

| # | Punto | Estado | Detalle |
|---|---|:--:|---|
| 1 | **Estado del servidor STAGING** | ✅ | `up 1 día 2:39`, load 0.20/0.35/0.42 (sano). Contenedores STAGING vivos: `odoo-lab` (Up 20h), `coc-gw-staging` (Up 24h, healthy), `coc-web-staging` (Up 23h). |
| 2 | **Versión de Odoo** | ✅ | `odoo-lab` = **Odoo Server 18.0-20260619** (18.0 Community). |
| 3 | **Estado de la DB STAGING** | ✅ | `Sentinela_STAGING` = **1180 MB**, accesible, 1 conexión activa. PostgreSQL **16.14** (contenedor `odoo18-migration-db-1`, :5433). |
| 4 | **Respaldo previo (existencia + validez)** | ⚠ | Existen y son legibles respaldos de **PROD**: `~/backups/DB_Sentinela_V18_PREDEPLOY_RC1_20260627_0814.sql.gz` y `Sentinela_V18_pre_adelanto_global_30jun.dump` (91 MB). **NO existe un dump dedicado de `Sentinela_STAGING`** previo a tocar STAGING → **debe tomarse antes del `-u`** (requisito del plan §0). La DB del gateway STAGING es `sqlite:////tmp/coc_gw.db` (efímera, no requiere respaldo persistente). |
| 5 | **Estado del Gateway** | ⚠ | `coc-gw-staging` **running/healthy**, `/health` → `{"status":"ok","version":"0.3.2"}`. Está en **versión Sprint 1 (0.4.0 es el RC)** → la actualización es el objeto de la Etapa 3. Corre con `--network host`. |
| 6 | **Estado de la SPA** | ⚠ | `coc-web-staging` running, imagen `coc-web:staging`, puerto **:3080**, smoke `GET /login → 200`. En versión Sprint 1 (RC = 0.5.0) → la actualiza la Etapa 3. |
| 7 | **Variables de entorno requeridas** | ❌ | Las **base** están presentes y correctas: `COC_OTP_PROVIDER=evoapi`, `COC_WA_*` (SentinelaWA), **`COC_ODOO_BASE_URL=http://192.168.3.2:8075` (apunta a STAGING ✅)**, `COC_COC_SHARED_SECRET`, `COC_JWT_SECRET`, `COC_CORS_ORIGINS=…:3080`. **FALTAN las variables de pago del Sprint 2:** `COC_STRIPE_SECRET_KEY`, `COC_STRIPE_WEBHOOK_SECRET` (gateway) y `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` (SPA). Ver punto 8. |
| 8 | **Stripe en modo test (`pk_test`/`sk_test`/`whsec`)** | ❌ | **NO existe ninguna clave Stripe configurada** en el entorno. `grep -i stripe` sobre `/home/egarza/coc_gw_staging.env` y `/opt/sentinela_coc/.env` = **vacío**; el env vivo de `coc-gw-staging` y `coc-web-staging` no contiene variables Stripe. **No fueron provistas** (precondición del plan §0). **BLOQUEANTE.** |
| 9 | **Endpoint HTTPS y recepción de webhooks** | ⚠ | NPM (`nginx-proxy-manager`) publica **:80/:81/:443** y hay cert válido para `*.sentinela.mx`. Pero el **gateway STAGING es solo-LAN** (`ufw 8401/tcp ALLOW 192.168.3.0/24 — UAT LAN only`); **sin host público HTTPS**, Stripe (test) **no puede entregar webhooks** desde internet al gateway STAGING. Requiere decisión: (a) exponer un endpoint HTTPS de STAGING, o (b) usar **Stripe CLI `stripe listen --forward-to`** para reenviar a la LAN. Subordinado al punto 8. |
| 10 | **Certificados TLS** | ✅ | `api.sentinela.mx` resuelve por Cloudflare; cert **Let's Encrypt** `CN=sentinela.mx`, válido **29-jun-2026 → 27-sep-2026**. NPM :443 operativo. (Aplica al ingreso PROD; STAGING aún no tiene host público.) |
| 11 | **Conectividad Gateway ↔ Odoo ↔ SPA** | ✅ | `coc-gw-staging` → Odoo STAGING `:8075/web/health` = **200**; → Odoo `:8070` = **200**; SPA STAGING `/login` = **200**. |
| 12 | **Espacio disponible en disco** | ✅ | `/dev/sda2` 457G, **42% usado, 254G libres**; inodes 18%. Holgado para imágenes/dumps. |
| 13 | **Estado de Docker/Compose** | ✅ | Docker **29.2.1**, Docker Compose **v5.0.2**; daemon up (30/32 contenedores running, 544 imágenes). |
| 14 | **Plan de rollback validado** | ⚠ | Procedimiento documentado (`DEPLOY_RUNBOOK_COC_RC1.md` + plan §7): revertir `sentinela_api` a 18.0.0.2.0 (`-u`), restaurar dump, recrear imágenes previas del gateway/SPA. **Pendiente para validarlo:** (a) tomar el dump de `Sentinela_STAGING` (punto 4) y (b) **etiquetar/conservar las imágenes Sprint 1 actuales** (`coc-gw:0.3.2` / `coc-web:staging` / `sentinela_api 18.0.0.2.0`) como artefactos de reversión antes de sobrescribir. |
| 15 | **Riesgos detectados** | — | Ver §Riesgos. |

---

## Riesgos detectados antes del despliegue
1. **(Bloqueante) Sin credenciales Stripe test** — sin `sk_test`/`pk_test`/`whsec` no hay forma de levantar el motor de pagos en STAGING ni validar la Etapa 4 (pago con tarjeta test + webhook real). **Origen:** precondición §0 no cumplida.
2. **(Bloqueante/derivado) Variables de entorno de pago ausentes** — el gateway y la SPA de STAGING no tienen las variables Stripe; depende del punto 1.
3. **(Advertencia) Ingreso de webhooks a STAGING** — el gateway STAGING es solo-LAN; sin endpoint HTTPS público o Stripe CLI, el webhook real de la Etapa 4 no se puede ejercitar.
4. **(Advertencia) Falta respaldo dedicado de `Sentinela_STAGING`** — debe generarse antes de cualquier `-u` para garantizar rollback de datos.
5. **(Advertencia) Artefactos de reversión no fijados** — las imágenes/versiones Sprint 1 actuales deben preservarse (tag) antes de promover el RC, para revertir gateway/SPA/addon.
6. **(Informativo) STAGING está hoy en Sprint 1** (gw 0.3.2 · api 18.0.0.2.0 · SPA Sprint 1) — esperado; es exactamente lo que la Etapa 3 actualiza.

---

## Veredicto

❌ **HAY ELEMENTOS BLOQUEANTES (puntos 7 y 8).** El checklist **NO está completamente en verde**.

Conforme a la regla establecida, **se detiene el proceso y NO se solicita autorización para la Etapa 3.**

### Para desbloquear (acciones previas a re-correr el Pre-Flight)
1. **Proveer claves Stripe modo test:** `sk_test_…`, `pk_test_…` y `whsec_…` (+ acceso al dashboard Stripe para registrar el webhook).
2. **Definir la estrategia de webhook en STAGING:** endpoint HTTPS público para el gateway STAGING **o** Stripe CLI (`stripe listen --forward-to http://192.168.3.2:8401/v1/payments/webhook`).
3. **Generar dump de `Sentinela_STAGING`** y **etiquetar las imágenes/versión Sprint 1** como artefactos de rollback.

Cuando estos puntos estén resueltos, se re-ejecuta el Pre-Flight; **solo con todo en verde** se solicitará la autorización formal de la Etapa 3.

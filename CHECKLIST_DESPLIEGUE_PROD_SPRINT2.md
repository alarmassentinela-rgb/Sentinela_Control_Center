# Checklist de Despliegue a Producción — Sprint 2 (Cobranza)

**Release:** `coc-v1.2.0` (sobre RC4 `d4427b6`). Marcar cada casilla en la ventana. Leyenda: ✅ OK · ⚠ Advertencia · ❌ Detener.

## A. Precondiciones (antes de la ventana)
- [ ] Decisión Stripe **test-primero / live** tomada (§0 del plan).
- [ ] Claves Stripe disponibles (`sk_*`, `pk_*`) + webhook registrado en dashboard → `https://api.sentinela.mx/v1/payments/webhook` con su `whsec`.
- [ ] `portal.sentinela.mx` expuesto (NPM/Cloudflare → `coc-web-prod`). *(Hoy 404.)*
- [ ] `api.sentinela.mx` = 200 (gateway prod).
- [ ] **Dump pre-deploy de `Sentinela_V18`** generado y verificado (`pg_restore --list`).
- [ ] Imágenes prod actuales **re-etiquetadas** como rollback: `coc-gw:rollback-prod-sprint1`, `coc-web:rollback-prod-sprint1`.
- [ ] tar del `sentinela_api` 18.0.0.2.0 actual (rollback de código).
- [ ] Confirmado: `odoo-lab` monta `staging-addons` (STAGING aislado de PROD).
- [ ] Ventana + responsable de guardia confirmados.

## B. Paso A — `sentinela_api` 18.0.0.3.1 (V18)
- [ ] `rsync` del tag → `/home/egarza/odoo18-migration/addons/sentinela_api`.
- [ ] `-u sentinela_api -d Sentinela_V18` sin errores/CRITICAL.
- [ ] Reinicio de `odoo18-migration-web-1`.
- [ ] Módulo `18.0.0.3.1 [installed]`; `/health :8070 = 200`.

## C. Paso B — Gateway 0.4.2
- [ ] Imagen `coc-gw:0.4.2` construida desde el tag.
- [ ] `.env` prod con `COC_STRIPE_SECRET_KEY` / `COC_STRIPE_PUBLISHABLE_KEY` / `COC_STRIPE_WEBHOOK_SECRET`.
- [ ] `gateway-gateway-1` recreado (:8400, misma DB/red).
- [ ] `/health = 0.4.2`; rutas Sprint 2 presentes; config Stripe cargada; logs sin fuga de secretos.

## D. Paso C — SPA 0.6.0
- [ ] Imagen `coc-web:0.6.0` (build-args `NEXT_PUBLIC_API_BASE=https://api.sentinela.mx` + `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`).
- [ ] `coc-web-prod` (:3090) recreado.
- [ ] `portal.sentinela.mx/login = 200`; PaymentElement renderiza.

## E. Paso D — Webhook + smoke end-to-end
- [ ] Webhook entrega a `api.sentinela.mx/v1/payments/webhook` → `[200]`.
- [ ] Pago de prueba/piloto desde `portal.sentinela.mx` → "¡Pago confirmado!" → factura pagada en V18 → estado de cuenta actualizado → (reactivación si aplica).
- [ ] `account.payment` creado; sin doble aplicación (idempotencia); consola limpia.

## F. No-regresión Sprint 1 (PROD)
- [ ] Login OTP · Dashboard · Mis Servicios · Facturación-consulta OK.
- [ ] PROD Odoo estable; STAGING sin afectación.

## G. Cierre
- [ ] Push tag `coc-v1.2.0`.
- [ ] `RELEASE_NOTES_SPRINT2_COC.md` + `ACTA_LIBERACION_SPRINT2_COC.md` completadas (digests, smoke, incidencias).
- [ ] Limpieza STAGING (listener CLI, contenedores UAT, ufw 8401).
- [ ] Backlog Sprint 3 abierto (OBS-2 + usuario técnico vs SUPERUSER_ID).

## Criterio GO / NO-GO
**GO** solo si: A–F en verde, 0 ❌, smoke del pago correcto, no-regresión Sprint 1, rollback disponible y probado en su procedimiento. Cualquier ❌ → **detener y ejecutar rollback** del componente afectado.

# Plan de Despliegue a Producción — Sprint 2 (Vertical Cobranza)

**RC aprobado:** `coc-v1.2.0-rc4` (commit `d4427b6`) → release final **`coc-v1.2.0`** (tag preparado, sin push hasta autorización).
**Componentes:** Gateway **0.4.2** · SPA **0.6.0** · `sentinela_api` **18.0.0.3.1**.
**Estado:** PLAN para tu revisión. **No se ejecuta ningún paso sin tu autorización explícita + ventana.**
**Base:** lecciones aprendidas en STAGING (aislamiento de addons, dos defectos críticos corregidos, UAT completa en verde con `EVIDENCIA_UAT_SPRINT2.md`).

---

## 0. DECISIÓN CRÍTICA previa — Stripe LIVE (cobros reales)
En STAGING se usó Stripe **test** + Stripe CLI (sin exponer el gateway). En Producción, para que un cliente pague de verdad se requiere **Stripe modo LIVE**, lo que implica **cargos reales a tarjetas**. Esto exige:
- **Claves LIVE:** `sk_live_…`, `pk_live_…`.
- **Webhook LIVE registrado en el dashboard de Stripe** apuntando a **`https://api.sentinela.mx/v1/payments/webhook`** (público, verificado 200) → genera su propio **`whsec_live`** (NO se usa Stripe CLI en prod).
- **Consideración PCI:** el PAN se captura en Stripe Elements (no toca nuestros servidores) → alcance SAQ-A. No loguear datos de tarjeta.
- **Alternativa de arranque conservador (recomendada para el primer día):** desplegar el código en prod pero mantener **Stripe test** unos días con un cliente piloto, y **hacer el corte a LIVE** en una segunda ventana corta. *(A decidir por ti.)*

> **Sin esta decisión (test-primero vs live directo) + las claves correspondientes, el despliegue funcional no puede completar el cobro real.**

## 1. Precondiciones (verificar ANTES de la ventana)
- [ ] **Decisión §0** tomada (test-primero o live directo) + claves Stripe correspondientes disponibles.
- [ ] **Webhook Stripe** (test o live) registrado a `https://api.sentinela.mx/v1/payments/webhook` con su `whsec`.
- [ ] **`portal.sentinela.mx` expuesto** (hoy responde 404): NPM/Cloudflare → SPA prod (`coc-web-prod`, host `:3090`). Sin esto, el cliente no llega al portal. *(Prerrequisito de negocio.)*
- [ ] **`api.sentinela.mx` operativo** (verificado 200) → gateway prod `127.0.0.1:8400`.
- [ ] **Respaldos:** dump fresco de `Sentinela_V18` (además del diario 08:00) + **etiquetar imágenes prod actuales** para rollback (ver §5).
- [ ] **Aislamiento confirmado:** `odoo-lab` (STAGING) usa `staging-addons`; PROD usa `./addons` → el `-u` en V18 **no** afecta STAGING (lección aplicada; el riesgo del árbol compartido quedó resuelto).
- [ ] Ventana acordada (bajo tráfico) + responsable de guardia.

## 2. Artefactos a desplegar (idénticos al RC validado)
| Componente | Actual PROD | Objetivo | Fuente |
|---|---|---|---|
| `sentinela_api` | 18.0.0.2.0 (V18) | **18.0.0.3.1** | tag `coc-v1.2.0` → `sentinela_api/` |
| Gateway | 0.3.2 (`coc-gateway:dev`) | **0.4.2** | tag → `sentinela_coc/gateway` (imagen horneada) |
| SPA | Sprint 1 (`coc-web:prod`) | **0.6.0** | tag → `sentinela_coc/web` (build con `pk_live`/`pk_test` + `NEXT_PUBLIC_API_BASE=https://api.sentinela.mx`) |

## 3. Orden de despliegue (con verificación por paso)
> Regla: cada paso verifica antes de continuar. PROD Odoo NO comparte proceso con STAGING; el `-u` en V18 es independiente.

**Paso A — `sentinela_api` 18.0.0.3.1 en V18**
1. `rsync` de `sentinela_api/` (del tag) → `/home/egarza/odoo18-migration/addons/sentinela_api` (path de PROD; STAGING ya no lo comparte).
2. Backup previo del código reemplazado (tar del `sentinela_api` actual) para rollback de archivos.
3. `-u sentinela_api -d Sentinela_V18` (reiniciar el contenedor `odoo18-migration-web-1` tras el `-u`).
4. **Verificar:** módulo `18.0.0.3.1 [installed]`; endpoints internos vivos (`/coc/internal/payments/apply` responde forbidden sin secreto); `/health :8070 = 200`; sin errores en log.

**Paso B — Gateway 0.4.2 (con Stripe + whsec)**
1. Build imagen `coc-gw:0.4.2` desde el tag.
2. Actualizar `.env` del gateway prod con `COC_STRIPE_SECRET_KEY`, `COC_STRIPE_PUBLISHABLE_KEY`, `COC_STRIPE_WEBHOOK_SECRET` (según §0) — **enmascarados, nunca commit**.
3. Recrear `gateway-gateway-1` con la imagen 0.4.2 (mismo compose/red/puerto :8400, misma DB `gateway-gateway-db-1`).
4. **Verificar:** `/health = 0.4.2`; rutas Sprint 2 presentes (`/v1/payments/start|webhook`, `/v1/ledger/statement|indicators`); config Stripe cargada; sin fuga de secretos en logs.

**Paso C — SPA 0.6.0**
1. Build imagen `coc-web:0.6.0` con `--build-arg NEXT_PUBLIC_API_BASE=https://api.sentinela.mx` + `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=<pk según §0>`.
2. Recrear `coc-web-prod` (:3090) con la nueva imagen.
3. **Verificar:** `/login = 200`; el PaymentElement de Stripe renderiza; `portal.sentinela.mx` sirve la SPA.

**Paso D — Webhook + smoke end-to-end**
1. Confirmar el webhook Stripe (test/live) entrega a `api.sentinela.mx/v1/payments/webhook` (evento de prueba → `[200]`).
2. **Smoke controlado:** un pago con **tarjeta de prueba** (si §0=test) o un **cargo piloto mínimo reembolsable** (si §0=live) desde `portal.sentinela.mx` → confirmación en UI → factura pagada en V18 → (reactivación si aplica) → estado de cuenta actualizado.
3. **Verificar:** `account.payment` creado, sin doble aplicación, auditoría/métricas OK, consola limpia.

## 4. Verificaciones post-deploy (criterios de aceptación)
- Los 3 componentes en su versión objetivo y saludables.
- Smoke del pago end-to-end en verde (según §0).
- **No-regresión del Sprint 1** en prod (login OTP, dashboard, servicios, facturación-consulta).
- PROD Odoo estable; STAGING sin afectación (aislamiento).

## 5. Estrategia de ROLLBACK (por componente, preparada ANTES de tocar prod)
| Componente | Artefacto de reversión | Procedimiento |
|---|---|---|
| **DB V18** | Dump pre-deploy (`DB_Sentinela_V18_PREDEPLOY_SPRINT2_<ts>.sql.gz`) + diarios | Restaurar dump si hubo migración de datos que revertir |
| **`sentinela_api`** | tar del código 18.0.0.2.0 (Paso A.2) + rama `main` (`8e311df`) | Restaurar código 18.0.0.2.0 → `-u sentinela_api` en V18 → restaurar dump si aplica |
| **Gateway** | Imagen `coc-gateway:dev` (0.3.2) actual → **re-tag inmutable** `coc-gw:rollback-prod-sprint1` | Recrear `gateway-gateway-1` desde la imagen de rollback + `.env` sin claves Stripe |
| **SPA** | Imagen `coc-web:prod` actual → **re-tag inmutable** `coc-web:rollback-prod-sprint1` | Recrear `coc-web-prod` desde la imagen de rollback |
| **Webhook Stripe** | — | Deshabilitar el endpoint en el dashboard de Stripe |

**Criterio de rollback:** cualquier fallo del smoke que comprometa cobros o estabilidad de prod → revertir el/los componente(s) afectado(s) en orden inverso (SPA → Gateway → api) y, si se tocó la DB, restaurar el dump. **El aislamiento garantiza que un rollback de prod no afecta STAGING.**

## 6. Riesgos y mitigaciones
1. **Cobros reales (§0):** mitigar arrancando en test o con piloto reembolsable.
2. **Webhook público:** `api.sentinela.mx` ya expone el gateway (200) — validar firma `whsec` live; endpoint idempotente (probado).
3. **`portal.sentinela.mx` 404:** exponerlo es prerrequisito; sin él no hay flujo de cliente.
4. **Deps del gateway por rango** (`requirements.txt` `>=`): pinear versiones resueltas para el build de prod (reproducibilidad).
5. **Reactivación doble (OBS-2):** comportamiento correcto (servicio reactivado); sin impacto; diferido a Sprint 3.

## 7. Post-liberación
- Tag `coc-v1.2.0` (push) + `RELEASE_NOTES_SPRINT2_COC.md` + `ACTA_LIBERACION_SPRINT2_COC.md` (completar con digests/smoke).
- Limpieza de STAGING (listener Stripe CLI, contenedores UAT `coc-gw-staging`/`coc-web-staging`, regla ufw 8401, límites OTP).
- Abrir backlog Sprint 3 (OBS-2 + usuario técnico que sustituya `SUPERUSER_ID` en `apply`).

> **No se ejecuta ningún paso sin tu autorización + ventana. Este plan, el checklist, la estrategia de rollback y las release notes se entregan para tu revisión previa.**

---

## 8. Lecciones aprendidas (para futuras liberaciones)
- **INC-V1-01 — reemplazo de un addon en PROD requiere `sudo` (o limpiar `__pycache__`):** al desplegar `sentinela_api`, Odoo (que corre como **root** dentro del contenedor) deja archivos `.pyc` en `__pycache__` propiedad de root. Un `rm -rf`/rsync del módulo ejecutado como el usuario `egarza` **falla con "Permission denied"** en esos `.pyc`; con `set -e` el script aborta dejando el directorio a medio reemplazar. **Regla para el Paso A:** hacer el reemplazo del árbol del addon con `sudo` (`sudo rm -rf <addon>` + `sudo tar/rsync` + `sudo chown -R egarza:egarza <addon>`), o limpiar primero `find <addon> -name __pycache__ -exec sudo rm -rf {} +`. **Mitigación de seguridad:** producción **no se reinicia** hasta después del reemplazo+`-u`, por lo que un fallo en este paso NO impacta a usuarios (el proceso vivo sigue con el código anterior en RAM); ante un directorio a medio reemplazar, **remediar el disco a un estado consistente antes de cualquier restart**.

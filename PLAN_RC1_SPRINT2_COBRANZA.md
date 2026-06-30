# Plan de Release Candidate (RC1) — Sprint 2 (Vertical COBRANZA)

**Estado:** PLAN para tu revisión. **No se ejecuta ninguna etapa sin tu autorización.**
**Rama:** `sprint2-cobranza` **CONGELADA** (solo bugs / ajustes de integración / cambios de despliegue; cualquier mejora → **backlog Sprint 3**).
**Congelado:** arquitectura, filosofía de evolución y spec del Sprint 2.
**Base:** Acta `CIERRE_TECNICO_SPRINT2_COBRANZA.md` (desarrollo concluido). Misma disciplina que el Sprint 1.

## Regla de avance (gate)
Cada etapa produce su **evidencia**; **no se avanza a la siguiente sin que la evidencia esté completa y aprobada por Enrique**. Si una validación crítica falla → se detiene, se documenta y se corrige antes de continuar.

---

## 0. Precondiciones y DECISIONES a confirmar (antes de la Etapa 1)
- [ ] **Alcance del release (IMPORTANTE):** la rama contiene, además de la vertical Cobranza, **cambios de `sentinela_subscriptions`** (cobro adelantado global — **+484/−71 en 10 archivos**) hechos en paralelo. **Decisión requerida:**
  - (a) **Liberar juntos** (Cobranza + Suscripciones) → ambos entran al RC y se validan en UAT; **o**
  - (b) **Separar** (release de Cobranza solo) → aislar los cambios de Suscripciones en otra rama/release.
  *Recomendación: confirmarlo explícitamente; el RC y el despliegue cambian según la decisión.*
- [ ] **Cuenta Stripe (modo test):** disponer de `sk_test_…`, `pk_test_…` y `whsec_…`; acceso al dashboard de Stripe para registrar el endpoint de webhook.
- [ ] **STAGING del Sprint 2:** se acepta **descongelar/actualizar STAGING** (Sentinela_STAGING + gateway/SPA de STAGING) a Sprint 2 para la validación viva. (Producción intacta hasta la Etapa 7.)
- [ ] **Respaldos disponibles** (DB gateway, DB Odoo, imágenes) antes de tocar STAGING y, luego, Producción.
- [ ] **Esquema de versionado** (propuesto):
  | Componente | Prod hoy | RC Sprint 2 |
  |---|---|---|
  | Gateway | 0.3.2 | **0.4.0** |
  | SPA | (Sprint 1) | **0.5.0** (ya bumpeada) |
  | sentinela_api | 18.0.0.2.0 | **18.0.0.3.0** |
  | Umbrella (tag) | `coc-v1.1.0-rc1` | **`coc-v1.2.0-rc1`** → `coc-v1.2.0` |

---

## Etapa 1 — Preparación del Release Candidate (RC1)
**Objetivo:** congelar un RC reproducible del Sprint 2.
**Entregables:**
- Bumps de versión (gateway 0.4.0, sentinela_api 18.0.0.3.0; SPA 0.5.0 ya hecha).
- Commit de cierre + **tag `coc-v1.2.0-rc1`** (rama congelada → el tag es el RC).
- **`RC_SPRINT2_COC.md`** (manifiesto): commits incluidos (S2-000…S2-015 + decisión sobre Suscripciones), versiones finales, identidad de artefactos (imágenes/digests que se construirán), confirmación "código validado == RC", mapa de rollback a versiones inmediatamente anteriores.

**Checklist de validación:**
- [ ] Árbol relevante limpio y pusheado; tag creado y en GitHub.
- [ ] Versiones bumpeadas y coherentes en los 3 componentes.
- [ ] Manifiesto con la lista exacta de commits y el alcance resuelto (decisión §0).

**Criterios de aceptación:** RC tageado + manifiesto completo + paridad declarada.
**Evidencia:** `RC_SPRINT2_COC.md`, hash del tag, salida de `git log`/`git describe`.

## Etapa 2 — Validación técnica del RC
**Objetivo:** demostrar que el RC está verde antes de tocar STAGING.
**Entregables:** corrida de pruebas sobre el RC (entorno de integración separado).
**Checklist de validación:**
- [ ] Gateway suite unitaria **148 passed / 8 skipped**.
- [ ] Aceptación E2E §12 **7/7** (`e2e_sprint2_cobranza.py`).
- [ ] SPA: typecheck + lint + build limpios; **4/4 estados** (Playwright).
- [ ] Sintaxis de los controllers Odoo nuevos (ledger/payments/cfdi/reactivation/notifications) OK.
- [ ] Paridad: el código del RC == lo que se ejecutará (md5/commit).

**Criterios de aceptación:** todo verde, sin regresión.
**Evidencia:** logs de pytest, build SPA, reporte de validación técnica.

## Etapa 3 — Despliegue a STAGING (Odoo + Stripe en modo test)
**Objetivo:** dejar el Sprint 2 corriendo **en vivo** en STAGING para validar lo que en desarrollo se probó con Fakes.
**Entregables:**
- `sentinela_api` (RC) en `Sentinela_STAGING`: rsync + `-u` + reinicio del contenedor (registra los `/coc/internal/{payments,cfdi,reactivation,notify}` + `/v1/ledger/movements`).
- Gateway **0.4.0** en STAGING (rebuild + recreate) con `.env` de STAGING + **claves Stripe test** (`COC_STRIPE_SECRET_KEY`/`WEBHOOK_SECRET`).
- SPA de STAGING reconstruida (con `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` test).
- **Webhook de Stripe (test)** registrado apuntando al endpoint de STAGING.

**Checklist de validación (humo):**
- [ ] `/health` gateway STAGING = 0.4.0; rutas Sprint 2 presentes (`/v1/payments/start`, `/v1/payments/webhook`, `/v1/ledger/statement`, `/v1/ledger/indicators`).
- [ ] Odoo STAGING responde los `/coc/internal/*` nuevos (200/forbidden según secreto), `/v1/ledger/movements` vivo.
- [ ] Stripe test: `providers/health`/conectividad OK; webhook test entrega.
- [ ] STAGING del Sprint 1 (lo ya liberado) **sin regresión**.

**Criterios de aceptación:** stack Sprint 2 levantado en STAGING, endpoints vivos, sin romper lo existente.
**Evidencia:** salidas de despliegue, smoke de endpoints, captura de la config del webhook Stripe.

## Etapa 4 — Ejecución de pruebas de validación (UAT)
**Objetivo:** validar **end-to-end real** la vertical (lo que el E2E de desarrollo faked).
**Entregables:** UAT sobre STAGING con **tarjetas de prueba de Stripe**.
**Checklist de validación (criterios §12, EN VIVO):**
- [ ] **Pago con tarjeta test** desde la SPA → PaymentIntent → confirmación.
- [ ] Webhook real Stripe → `pago.confirmado` → **aplicación** → `factura.pagada` (factura liquidada en Odoo).
- [ ] **CFDI** timbrado (Prodigia test) o **pendiente reintetable** sin invalidar el pago.
- [ ] **Reactivación por servicio** (suscripción suspendida → reactivada solo si cumple las 3 condiciones).
- [ ] **Notificación** al cliente por el canal existente.
- [ ] **Estado de Cuenta** actualizado **desde el Ledger**.
- [ ] **Idempotencia** (webhook duplicado / reintento → una sola aplicación) y **conciliación** (no duplica con depósito) reales.
- [ ] Tarjeta rechazada → mensaje claro, sin aplicar; "en proceso" manejado.
- [ ] Consola limpia; aislamiento por cliente intacto.

**Criterios de aceptación:** todos los casos §12 en verde con Odoo + Stripe vivos.
**Evidencia:** `EVIDENCIA_UAT_SPRINT2.md` (casos ejecutados/aprobados/rechazados, capturas, IDs de pago/CFDI), igual formato que la UAT del Sprint 1.

## Etapa 5 — Corrección de incidencias (si existen)
**Objetivo:** cerrar SOLO defectos detectados en UAT (sin features).
**Entregables:** fixes mínimos en la rama congelada + re-prueba de la incidencia + no-regresión.
**Checklist:** [ ] cada incidencia con causa/fix/evidencia; [ ] suite + UAT del caso afectado en verde.
**Criterios de aceptación:** 0 incidencias bloqueantes abiertas.
**Evidencia:** bitácora de incidencias y correcciones.

## Etapa 6 — Release Candidate final (si aplica)
**Objetivo:** si hubo fixes, re-cortar el RC.
**Entregables:** bump menor + **tag `coc-v1.2.0-rc2`** + manifiesto actualizado + re-validación técnica (Etapa 2).
**Criterios de aceptación:** RC final verde y aprobado.
**Evidencia:** manifiesto RC final + corrida verde.

## Etapa 7 — Liberación a Producción
**Objetivo:** promover el RC aprobado a Producción, ventana controlada.
**Entregables:** **`PLAN_DESPLIEGUE_PROD_SPRINT2_COC.md`** (precondiciones, respaldos, orden exacto, verificaciones, smoke, rollback por componente, ventana estimada) + ejecución bajo autorización.
**Orden (sujeto a la decisión §0):** sentinela_api (V18, `-u` + restart) → Gateway 0.4.0 (claves Stripe **live**) → SPA prod → webhook Stripe **live** → smoke.
**Checklist/criterios:** smoke post-deploy en verde + no-regresión RC1 (Sprint 1) + observabilidad.
**Evidencia:** acta de despliegue (digests de imágenes prod, resultados de smoke).
> **No se ejecuta sin tu autorización explícita + ventana.**

## Etapa 8 — Tag de versión y documentación de la release
**Entregables:** **tag `coc-v1.2.0`** (release final) + `RELEASE_NOTES_SPRINT2_COC.md` + **`REPORTE_LIBERACION_SPRINT2_COC.md`** (componentes promovidos, versiones desplegadas, smoke, incidentes, estado final), formato del Sprint 1.
**Criterios de aceptación:** tag publicado + reporte de liberación completo.
**Evidencia:** los documentos + el tag.

## Etapa 9 — Cierre formal del Sprint 2
**Entregables:** declaración de cierre + actualización de memoria del proyecto (Sprint 2 en PROD) + apertura del **backlog Sprint 3** (mejoras diferidas registradas).
**Criterios de aceptación:** Sprint 2 liberado y validado en Producción; cierre declarado por Enrique.
**Evidencia:** acta de cierre del Sprint 2.

---

## Resumen de evidencia por etapa
| Etapa | Documento/evidencia |
|---|---|
| 1 | `RC_SPRINT2_COC.md` + tag `coc-v1.2.0-rc1` |
| 2 | Reporte de validación técnica (pytest/build) |
| 3 | Smoke de despliegue STAGING + config webhook |
| 4 | `EVIDENCIA_UAT_SPRINT2.md` |
| 5 | Bitácora de incidencias |
| 6 | RC final (`-rc2`) si aplica |
| 7 | `PLAN_DESPLIEGUE_PROD_SPRINT2_COC.md` + acta de despliegue |
| 8 | tag `coc-v1.2.0` + `RELEASE_NOTES` + `REPORTE_LIBERACION_SPRINT2_COC.md` |
| 9 | Acta de cierre del Sprint 2 |

**No se desarrolla funcionalidad nueva. No se ejecuta ninguna etapa sin tu autorización.** Comenzamos por la **Etapa 1** una vez que confirmes la **decisión §0 (alcance / Suscripciones)** y apruebes este plan.

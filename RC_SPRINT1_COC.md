# Release Candidate — Sprint 1 (Portal COC)

**RC oficial:** `coc-v1.1.0-rc1` · **Base (último prod):** `coc-v1.0.0` · **Fecha:** 2026-06-29
**Estado:** EN ESPERA DE APROBACIÓN EXPLÍCITA. **No desplegado.**

> Esquema de versionado: tags `coc-vX.Y.Z` (umbrella del Portal COC). RC = sufijo `-rcN`.
> `coc-v1.0.0` = RC1/identidad ya en prod (27-jun). `coc-v1.1.0` = incremento **Sprint 1** (Mis Servicios + Facturación).

---

## 1. Commit final del footer del Login ✅

- **`29f7d66`** — `feat(web): pie institucional en Login (cosmético UAT Sprint 1) — SPA 0.4.1`
- Archivos: `sentinela_coc/web/app/login/page.tsx` (+8/−1), `sentinela_coc/web/.gitignore` (+1), `sentinela_coc/web/package.json` (0.3.5→0.4.1).
- Es el **HEAD** del RC.

## 2. Tag de release

- **`coc-v1.1.0-rc1`** → apunta al commit de cierre del RC (HEAD del Sprint 1, incluye el manifiesto y la evidencia).

## 3. Lista exacta de commits incluidos en el RC

Rango `coc-v1.0.0..coc-v1.1.0-rc1` (paths `sentinela_coc` + `sentinela_api`) — **26 commits**:

| # | Commit | Descripción |
|---|---|---|
| 1 | `29f7d66` | feat(web): pie institucional en Login (cosmético UAT) — SPA 0.4.1 |
| 2 | `e5168a9` | feat(web): lote DS — tokens, tipografía, glosario, a11y, paginación (0.4.0) |
| 3 | `e52e9c5` | refactor(web): StatusIndicator sin referencia de dominio |
| 4 | `fe62424` | refactor(web): indicador de estado → componente DS reutilizable |
| 5 | `0f709df` | fix(web): Estado de Tranquilidad — composición flex+gap + indicador SVG |
| 6 | `7db1eb0` | chore(web): favicon (app/icon.svg) → elimina 404 /favicon.ico |
| 7 | `3fed276` | fix(web): recuperación de sesión robusta — guard único + sync multi-pestaña |
| 8 | `13d45d1` | fix(web): flujo único de recuperación de sesión (401 → /login?expired=1) |
| 9 | `69963ed` | refactor(web): BrandMark única fuente de identidad (logo+título) |
| 10 | `6062187` | fix(web): login con identidad unificada — BrandMark |
| 11 | `c4fbd27` | style(web): acabado UI del encabezado |
| 12 | `74cbbb9` | style(web): pulido final del encabezado |
| 13 | `b26841d` | style(web): encabezado compacto y jerarquizado |
| 14 | `885f2a6` | style(web): header — logo + 'Portal del Cliente' bold |
| 15 | `61014c6` | fix(web): logo — identidad visual desde Odoo (fallback nombre) |
| 16 | `ce34fb8` | feat(coc): lote UAT 1-5 — identidad + acciones + servicios + pago UX + proxy /v1/me |
| 17 | `bb18d80` | fix(gateway): targets de Próximas acciones a rutas reales |
| 18 | `d71bfad` | feat(web): dashboard reequilibrado + Historial de Pagos |
| 19 | `7a722fc` | feat(web): layout responsive/adaptive (Mobile First → escritorio) |
| 20 | `170b63f` | fix(web): mensaje de verificación OTP según el error real |
| 21 | `0656bab` | fix(gateway): normalizar teléfono a E.164 MX antes de EvoApi |
| 22 | `5b7f113` | test(coc): E2E STAGING Sprint 1 (13/13) + CORS + evidencia |
| 23 | `dbc6544` | feat(web): Sprint 1 paso 3 — SPA residencial (Dashboard + Servicios + Facturación) |
| 24 | `654ffe0` | docs(coc): contrato OpenAPI v1 con ejemplos |
| 25 | `fd16437` | feat(gateway): Sprint 1 paso 2 — proxy de negocio act-as + dashboard + caché |
| 26 | `cc81f39` | feat(sentinela_api): Sprint 1 paso 1 — endpoints Mis Servicios + Facturación + DTOs |

*(El commit de documentación del RC —reporte UAT, plan de despliegue, este manifiesto y la evidencia— se añade encima y es el objeto al que apunta el tag.)*

## 4. Versiones finales de los componentes

| Componente | Versión RC | Fuente de verdad |
|---|---|---|
| **Gateway (BFF)** | **0.3.2** | `sentinela_coc/gateway/app/main.py` → `version="0.3.2"` |
| **SPA** | **0.4.1** | `sentinela_coc/web/package.json` → `"version": "0.4.1"` |
| **sentinela_api** (Odoo addon) | **18.0.0.2.0** | `sentinela_api/__manifest__.py` (= instalado en V18) |

## 5. Identificación de las imágenes Docker

> Nota de método: el **gateway de STAGING** corre con el runtime en imagen + **bind-mount del código** (`/home/egarza/coc_gateway_build → /app`); por eso la identidad real del código validado es el **fuente** (verificado por md5 contra el repo), no el digest de la imagen base. En **PROD** el gateway y la SPA se construyen **frescos desde el tag del RC** (`docker compose up --build` / `docker build`), por lo que sus digests se generan en la ventana y se registran en el acta de despliegue.

### Imágenes/artefactos VALIDADOS en la UAT (referencia)
| Artefacto | ID / digest | Notas |
|---|---|---|
| Gateway runtime (STAGING) | `coc-gateway:test` · `sha256:6a411ac7274e61c60e115ff31566fbf206d0685d7cfc678eab0fd183dd1faa51` | base de runtime; **código por bind-mount** = fuente del RC (md5 `portal.py`=`57a2c1d8f8c0e2d99bb576eb157b1bcd` == repo) |
| SPA (STAGING, con footer) | `coc-web:staging` · `sha256:dca316c4eef203b930dc23675cbd9da3a2843f86d8ffc2abe3cf1d34dd812d01` | **baked** (Next standalone) desde el fuente del RC; `NEXT_PUBLIC_API_BASE=http://192.168.3.2:8401` (staging) |
| sentinela_api (V18 y lab) | módulo `installed 18.0.0.2.0` | sin imagen (addon Odoo); código en disco md5 == repo |

### Imágenes que se DESPLEGARÁN en PROD (se construyen en la ventana desde `coc-v1.1.0-rc1`)
| Artefacto prod | Construcción | Diferencia vs staging |
|---|---|---|
| `coc-gateway:dev` (nuevo) | `docker compose up -d --build` en `/opt/sentinela_coc/gateway` | mismo fuente; `.env` de prod (Odoo `:8070`, secretos prod) |
| `coc-web:prod` (nuevo) | `docker build --build-arg NEXT_PUBLIC_API_BASE=https://api.sentinela.mx` | **solo** cambia la URL base (horneada); código idéntico |
| sentinela_api | **sin cambio** (ya instalado y con rutas vivas en V18) | — |

> El digest de cada imagen de prod se capturará al construirla y quedará asentado en el acta de despliegue, junto al commit `coc-v1.1.0-rc1` que las originó (reproducibilidad por fuente).

## 6. Confirmación: código UAT == código del RC ✅

- **Paridad gateway** (md5 fuente STAGING vs repo): `portal.py`, `auth.py`, `main.py`, `clients/odoo.py` → **idénticos**.
- **Paridad SPA Login** (lo que más cambió): `git show HEAD:.../login/page.tsx` md5 = **`f1c933a6df50257e9fbdc0edbb72eba4`** == `/opt/sentinela_coc/web/.../login/page.tsx` en el server (lo que sirvió el contenedor UAT) → **idénticos**.
- **Paridad sentinela_api** (md5 `billing.py` server vs repo) → **idénticos**; módulo `installed 18.0.0.2.0`.
- **Conclusión:** lo aprobado en la UAT corresponde **exactamente** al código del RC `coc-v1.1.0-rc1`.

## 7. Confirmación: rollback → versiones inmediatamente anteriores ✅

| Componente | Versión RC (nueva) | Versión inmediata anterior (rollback) | Mecanismo |
|---|---|---|---|
| Gateway | 0.3.2 (nueva imagen) | **0.2.0** — `coc-gateway:dev` · `sha256:938e10b3876d420f443474e08158ce72ac7f0037d015136e5b17aac9e70b3722` (imagen prod en ejecución HOY) | re-tag previo a la ventana (`coc-gateway:rollback-0.2.0`) + `compose up` a esa imagen |
| SPA | 0.4.1 (`coc-web:prod`) | **No existía en prod** | rollback = `docker rm -f coc-web-prod` (sin estado) |
| sentinela_api | 18.0.0.2.0 | **18.0.0.2.0 (sin cambio)** | N/A — no se toca V18 |
| Umbrella (tag) | `coc-v1.1.0` | **`coc-v1.0.0`** (prod actual) | checkout del tag previo si se requiere reconstruir |

- El plan de rollback de `PLAN_DESPLIEGUE_PROD_SPRINT1_COC.md §6` apunta a estas versiones inmediatamente anteriores. **DB del gateway** (postgres `coc_gateway`) se respalda antes de la ventana (§2).

---

## Veredicto del RC

✅ **Release Candidate `coc-v1.1.0-rc1` armado y consistente.** Código validado en UAT == código del RC; versiones y artefactos identificados; rollback mapeado a las versiones inmediatamente anteriores.

**Pendiente:** tu **aprobación explícita del RC**. Una vez aprobado, la siguiente orden será la **promoción controlada del Sprint 1 a producción** siguiendo `PLAN_DESPLIEGUE_PROD_SPRINT1_COC.md`. **Nada se despliega hasta entonces.**

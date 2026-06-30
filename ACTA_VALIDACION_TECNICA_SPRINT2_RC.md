# Acta de Validación Técnica — RC Sprint 2 (`coc-v1.2.0-rc1`)

**Etapa 2** del `PLAN_RC1_SPRINT2_COBRANZA.md` · **GATE INDEPENDIENTE** (no se apoya en la evidencia de paridad obtenida durante la preparación del RC — Etapa 1).
**Fecha:** 2026-06-30 · **Objeto validado:** tag `coc-v1.2.0-rc1` (commit `9616343`) en la rama `release/sprint2-cobranza`.
**Autorización:** Enrique aprobó la Etapa 1 y autorizó ejecutar la Etapa 2 como gate independiente. **No se despliega a STAGING ni se avanza a la Etapa 3 sin su aprobación formal.**
**Método:** **reconstrucción desde cero a partir del TAG** (no del working-tree): `git archive coc-v1.2.0-rc1` → transferencia al server (paridad md5 verificada en ambos extremos) → extracción en directorio limpio (`~/coc_rc2_gate`) → **build `--no-cache` de imágenes nuevas** (server `192.168.3.2`, Docker 29.2.1) → ejecución de las pruebas **dentro de la imagen recién construida**, con dependencias instaladas desde `requirements.txt`/`package-lock.json`. Cero pasos manuales.

---

## 1. Resultado por validación
| # | Validación | Resultado | Evidencia |
|---|---|---|---|
| 1 | **Integridad de la rama RC** | ✅ | `git fsck --full` sin errores (solo *dangling blobs*, normal); tag `coc-v1.2.0-rc1` → `9616343`, presente en GitHub (`origin`); HEAD (`74f7b76`) = tag **+1 commit solo-markdown** (este acta previa), `git describe`=`coc-v1.2.0-rc1-1-g74f7b76`; **aislamiento**: `diff main..HEAD -- sentinela_subscriptions` y `-- .claude` **vacíos** → RC es **solo Cobranza**; 20 commits `main..HEAD` |
| 2 | **Suite de pruebas automatizadas (completa)** | ✅ **148 passed / 8 skipped** (3.91s) | `python -m pytest -q` **dentro de `coc-gateway:rc2gate`** (deps recién instaladas). Los 8 *skipped* = E2E de STAGING (requieren `COC_E2E=1` + Odoo vivo, por diseño) |
| 3 | **E2E del Sprint 2 (§12)** | ✅ **7/7 PASS** | `tests/e2e_sprint2_cobranza.py -v` en la imagen fresca: happy_path · idempotente · conciliación · cfdi_pac_falla_pago_valido · reactivacion_por_servicio · estado_de_cuenta_desde_ledger · motor_sin_stripe |
| 4 | **Build del Gateway (`--no-cache`)** | ✅ EXIT=0 | `docker build --no-cache` desde el Dockerfile del RC; imagen `coc-gateway:rc2gate` digest `sha256:9645940fb1d3…` |
| 5 | **Build de la SPA** | ✅ EXIT=0 | `docker build` (Next standalone, `npm ci`); imagen `coc-web:rc2gate` digest `sha256:359f2683c04b…`; **smoke** `GET /login → 200` y `GET / → 200` en contenedor efímero |
| 6 | **Versiones y dependencias** | ✅ | **Gateway 0.4.0** (verificado en imagen, `app/main.py`) · **SPA 0.5.0** (`package.json`) · **sentinela_api 18.0.0.3.0** (manifest). Resueltas en imagen: `stripe` **12.5.1** (major 12 ∈ `>=9,<13` ✅), `fastapi` **0.138.2**, `sqlalchemy` **2.0.51**, `pydantic` **2.13.4**, `starlette` **1.3.1**. **Controllers Odoo nuevos**: `py_compile` de todo `sentinela_api` = **PY_COMPILE_OK**. **Rutas Sprint 2 presentes** (ver §2) |
| 7 | **Reconstrucción desde cero sin intervención manual** | ✅ | Fuente = **tag** vía `git archive` (md5 `237a5ac5…` idéntico origen↔server); ambas imágenes construidas **fresh** desde fuente + lockfile/requirements; la suite completa pasa con las deps recién instaladas; **cero pasos manuales** |
| 8 | **Warnings / anomalías** | ✅ (sin bloqueantes) | 3 *DeprecationWarning* de **librerías de terceros** (ver §3); **ninguno de código propio** |
| 9 | **Acta de validación técnica** | ✅ | este documento |

## 2. Evidencia generada
- **Imágenes de validación** (efímeras): `coc-gateway:rc2gate` (`sha256:9645940fb1d3…`), `coc-web:rc2gate` (`sha256:359f2683c04b…`). Se reconstruyen desde el tag. *Nota:* los digests difieren de los de la Etapa 1 (`ba75ec7d`/`6be4cc97`) por ser builds nuevos — lo reproducible es el **resultado** (suite verde, deps en rango), no el byte-a-byte de la imagen (deps por rango; ver Riesgo 2).
- **Salidas capturadas:** build gateway `--no-cache` EXIT=0; `pytest` **148/8** + e2e **7/7** dentro de la imagen fresca; build SPA EXIT=0 + smoke `/login`=200,`/`=200; `import stripe`→12.5.1 (en rango), fastapi/sqlalchemy/pydantic/starlette verificados en imagen; `py_compile` sentinela_api OK.
- **Rutas Sprint 2 confirmadas (paridad funcional):**
  - *Odoo (`sentinela_api`):* `/coc/internal/payments/apply`, `/coc/internal/cfdi/stamp`, `/coc/internal/reactivation/{service_state,reactivate}`, `/coc/internal/notify/payment_confirmed`, `/v1/ledger/movements` (auth='user').
  - *Gateway:* `/v1/payments/start`, `/v1/payments/webhook`, `/v1/ledger/statement`, `/v1/ledger/indicators`.
- **Integridad git:** fsck limpio; tag↔commit; tag en GitHub; aislamiento (diff vacío Suscripciones/skills); 20 commits `main..HEAD`.

## 3. Riesgos detectados
1. **Warnings de terceros (no bloqueantes):** `StarletteDeprecationWarning` (httpx en TestClient — solo pruebas), `passlib` (`crypt` deprecado en Py3.13) y `argon2.__version__`. Sin impacto funcional. **Recomendación:** atender en mantenimiento de dependencias, no en este release.
2. **Dependencias del Gateway por rango, sin lock con hash** (`requirements.txt` usa `>=`/rangos). La reconstrucción resolvió `stripe 12.5.1`, `fastapi 0.138.2`, etc. — funcionan, pero un build futuro podría resolver versiones distintas dentro del rango. **Recomendación (no bloqueante):** para el build de Producción, **pinear** las versiones resueltas (constraints o `pip freeze`) para reproducibilidad exacta. La SPA ya está pineada por `package-lock.json`.
3. **Validación viva pendiente (por diseño):** los E2E §12 se ejecutan aquí con puertos **Fake** (Odoo/Stripe). La integración con **Odoo + Stripe EN VIVO** se valida en STAGING (Etapas 3-4). Esta acta cubre integridad/pruebas/builds del RC, no la integración con externos.
4. **Nota de alcance del gate:** se validó el **tag** `coc-v1.2.0-rc1`; HEAD de la rama está 1 commit adelante (`74f7b76`), exclusivamente documentación (el acta previa) — no afecta código ni imágenes.

## 4. Conclusión técnica
El RC `coc-v1.2.0-rc1` es **íntegro, aislado (solo Cobranza) y reproducible desde cero a partir del tag**: ambas imágenes se construyen sin intervención manual y, dentro de la imagen recién construida, la suite completa (**148 passed / 8 skipped**) y la aceptación E2E §12 (**7/7**) pasan con dependencias recién instaladas. Versiones coherentes en los 3 componentes (Gateway 0.4.0 · SPA 0.5.0 · sentinela_api 18.0.0.3.0), `stripe` dentro del rango, controllers Odoo con sintaxis válida y rutas del Sprint 2 presentes. Sin warnings/anomalías bloqueantes (los 3 *DeprecationWarning* son de terceros). **Este gate independiente reproduce y confirma el resultado de la Etapa 1.**

## 5. Recomendación
✅ **APROBAR el RC `coc-v1.2.0-rc1` para avanzar a STAGING (Etapa 3).**
Sugerencias no bloqueantes a ejecutar **durante** la liberación: pinear las deps del Gateway para el build de Producción (Riesgo 2); atender los *DeprecationWarning* en un mantenimiento posterior (Riesgo 1).

> **No se desplegó a STAGING ni se avanzó a la Etapa 3.** A la espera de la **aprobación formal de la Etapa 2** por parte de Enrique.

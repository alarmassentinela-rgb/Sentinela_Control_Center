# Acta de Validación Técnica — RC Sprint 2 (`coc-v1.2.0-rc1`)

**Etapa 2** del `PLAN_RC1_SPRINT2_COBRANZA.md` · **Gate independiente** (no se apoya en la evidencia de paridad de la Etapa 1).
**Fecha:** 2026-06-30 · **Objeto validado:** rama `release/sprint2-cobranza` / tag `coc-v1.2.0-rc1`.
**Método:** **reconstrucción desde cero** del fuente del RC en un directorio limpio (`/home/egarza/coc_rc2`), construyendo las imágenes **sin reusar artefactos previos** y ejecutando las pruebas dentro de la imagen recién construida.

---

## 1. Resultado por validación
| # | Validación | Resultado | Evidencia |
|---|---|---|---|
| 1 | **Integridad de la rama RC** | ✅ | `git fsck` sin errores; tag `coc-v1.2.0-rc1` apunta a HEAD; `diff main..HEAD -- sentinela_subscriptions` y `-- .claude` **vacíos** (solo Cobranza); 18 commits |
| 2 | **Suite de pruebas automatizadas (completa)** | ✅ **148 passed / 8 skipped** | corrida **dentro de la imagen recién construida** (`coc-gateway:rc2`) con deps instaladas desde `requirements.txt` |
| 3 | **E2E del Sprint 2 (§12)** | ✅ **7/7 PASS** | `tests/e2e_sprint2_cobranza.py` en la imagen fresca |
| 4 | **Build del Gateway** | ✅ EXIT=0 | `docker build --no-cache` desde el Dockerfile del RC; imagen `sha256:ba75ec7d…` |
| 5 | **Build de la SPA** | ✅ EXIT=0 | `docker build` (Next standalone, `npm ci`); imagen `sha256:6be4cc97…`; smoke `GET /login → 200` |
| 6 | **Versiones y dependencias** | ✅ | Gateway **0.4.0** · SPA **0.5.0** · sentinela_api **18.0.0.3.0**; `stripe` resuelto a **12.5.1** (rango `>=9,<13`); fastapi 0.138.2 · sqlalchemy 2.0.51; `package-lock.json` presente (SPA) |
| 7 | **Reconstrucción desde cero sin intervención manual** | ✅ | ambas imágenes se construyeron **fresh** desde el fuente + lockfile/requirements, **cero pasos manuales**; la suite pasa con las deps recién instaladas |
| 8 | **Warnings / anomalías** | ✅ (sin bloqueantes) | 3 *DeprecationWarning* de **librerías de terceros** (ver §3); ninguno de código propio |
| 9 | **Acta de validación técnica** | ✅ | este documento |

## 2. Evidencia generada
- **Imágenes de validación** (efímeras, ya removidas): `coc-gateway:rc2` (`ba75ec7d`), `coc-web:rc2` (`6be4cc97`). Se reconstruyen idénticas desde el tag.
- **Salidas:** build gateway `--no-cache` EXIT=0; `pytest` 148/8 + e2e 7/7 en imagen fresca; build SPA EXIT=0 + `/login` 200; `import stripe`→12.5.1 en la imagen.
- **Integridad git:** fsck limpio; tag↔HEAD; aislamiento (diff vacío Suscripciones/skills).

## 3. Riesgos detectados
1. **Warnings de terceros (no bloqueantes):** `StarletteDeprecationWarning` (httpx en TestClient — solo pruebas), `passlib` (`argon2.__version__`, `crypt` deprecado en Py3.13). Sin impacto funcional; **recomendación:** atender en mantenimiento de dependencias (no en este release).
2. **Dependencias del Gateway por rango, sin lock con hash** (`requirements.txt` usa `>=`). La reconstrucción resolvió `stripe 12.5.1`, `fastapi 0.138.2`, etc. — funcionan, pero una build futura podría resolver versiones distintas dentro del rango. **Recomendación (no bloqueante):** para el build de Producción, **fijar/pinear** las versiones resueltas (constraints o `pip freeze`) para reproducibilidad exacta. La SPA ya está pineada por `package-lock.json`.
3. **Validación viva pendiente (por diseño):** los endpoints internos de Odoo y la integración Stripe se validan **EN VIVO** en STAGING (Etapa 3-4); esta acta cubre la integridad/pruebas del RC, no la integración con externos.

## 4. Conclusión técnica
El RC `coc-v1.2.0-rc1` es **íntegro, aislado (solo Cobranza) y reproducible desde cero**: ambas imágenes se construyen sin intervención manual y la suite completa (148/8) + la aceptación E2E §12 (7/7) pasan con dependencias recién instaladas. Versiones coherentes. Sin warnings/anomalías bloqueantes.

## 5. Recomendación
✅ **APROBAR el RC `coc-v1.2.0-rc1` para avanzar a STAGING (Etapa 3).**
Sugerencias no bloqueantes para ejecutar **durante** la liberación: pinear deps del Gateway para el build de Producción (Riesgo 2); atender los *DeprecationWarning* en un mantenimiento posterior (Riesgo 1).

> No se desplegó a STAGING ni se avanzó a la Etapa 3. A la espera de la aprobación formal de la Etapa 2.

# distributor_syscom (conector de referencia)

Conector **Syscom** del Motor de Catálogo y **plantilla** para todos los distribuidores. Implementa el contrato `DistributorConnector` del SDK `distributor_connector_base`.

> Documenta **cómo es el código**. Diseño/decisiones en `BLUEPRINT_*` y `CATALOG_ENGINE_STANDARDS_*` del repo raíz; mapa de campos en `MAPEO_NORMALIZACION.md`.

- Connector `1.0.0`, requiere motor `>=1.0,<2.0`. Depende de `distributor_connector_base`. Odoo 18, DB lab `Sentinela_STAGING`.
- **Deploy:** rsync a `/home/egarza/odoo18-migration/addons/` → `-i/-u` en STAGING. **Aún NO en PROD.**

## Arquitectura
- **`lib/mapping.py`** (PURO): `normalize(raw)→NormalizedProduct`. Tolerante a nulos; `KNOWN_KEYS` → compat. hacia adelante (`raw._unknown_keys`); `is_error_payload()` (Syscom devuelve **HTTP 200 + `{"error":...}`** para no disponibles); `to_embedding_text()` (IA).
- **`lib/quality.py`** (PURO): `check(np)→[códigos]` (advertencias, no detiene) + `find_duplicates()`.
- **`lib/syscom_connector.py`**: `SyscomConnector(DistributorConnector)` registrado `@register_connector("syscom")`. Auth OAuth + caché de token (vía `config.get_secret/set_secret`); `_get()` central con rate-limit + circuit breaker + mapeo de errores (429→RateLimitError, 5xx/timeout/red→UpstreamUnavailable, 401→refresh+retry, JSON inválido→UpstreamUnavailable); **métricas por endpoint** (`self.metrics`, `metrics_summary()`). Sesión HTTP **inyectable** (`_session`) para pruebas sin red.
- **`hooks.py`** `post_init_hook`: siembra el backend `backend_syscom` y migra credenciales legacy `sentinela_syscom.*` a los secretos del backend.
- **`data/distributor_backend.xml`**: registro `distributor.backend` (connector_key=`syscom`).

## Reglas / trampas
- **lib sin Odoo** (excepto importar el SDK `distributor_connector_base.lib`): no importar `odoo` en `lib/` → testeable y portable.
- **Payload de error = HTTP 200 + `{"error":...}`** (NO 404). Siempre pasar por `is_error_payload`.
- **Precios en USD** (string) → `_to_float`; convertir a MXN es trabajo del motor (D3+), no del conector.
- **Imágenes/documentos solo URL** (sin binarios), respetando la política del backend.
- **Registro al cargar:** `lib/__init__` importa `syscom_connector` para que `@register_connector` se ejecute al instalar el addon.
- **Pruebas:** `tests/fixtures/*.json` son payloads REALES; `test_connector.py` usa `FakeSession` (sin red). Correr con `--test-tags /distributor_syscom`.

## No incluye (es de fases siguientes)
La **promoción** a `product.template`, el índice/caché persistido, la conversión USD→MXN, el scheduler por prioridad y la API REST son del **motor** (`product_catalog_engine`, D3+). Este módulo solo provee el conector + su normalización/calidad.

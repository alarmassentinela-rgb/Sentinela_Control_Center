# distributor_syscom — Conector de REFERENCIA (Catalog Engine)

Conector de **Syscom** para el Motor de Catálogo y **plantilla oficial** para todos los
distribuidores futuros (CVA, CT, Exel, Ingram, Intcomex, Tecnosinergia, …).

- Connector `1.0.0` · módulo Odoo `18.0.1.0.0` · requiere motor `>=1.0,<2.0`
- **Depende de:** `distributor_connector_base`

## Cómo construir un nuevo conector (siguiendo este ejemplo)
1. **Módulo** `distributor_<slug>` que dependa de `distributor_connector_base`.
2. **Conector** en `lib/<slug>_connector.py`:
   ```python
   @register_connector("<slug>", requires_engine=">=1.0,<2.0")
   class MiConnector(DistributorConnector):
       version = "1.0.0"
       def authenticate(self, force=False): ...      # auth + caché de token (config get/set_secret)
       def search(self, query, filters=None, page=1): ...
       def get_product(self, ref): ...
       def get_price_stock(self, refs): ...
       def normalize(self, raw): ...                 # delega a lib/mapping
   ```
   Reutiliza del SDK: `resilience.RateLimiter`, `resilience.CircuitBreaker`, `Session+Retry`,
   y mapea errores a `RateLimitError`/`UpstreamUnavailableError`/`AuthError`/`ConnectorError`.
3. **Mapeo puro** en `lib/mapping.py` (`normalize(raw) -> NormalizedProduct`), tolerante a
   nulos y con `KNOWN_KEYS` para compatibilidad hacia adelante. Documenta el mapa en
   `MAPEO_NORMALIZACION.md`.
4. **Calidad** en `lib/quality.py` (advertencias, no detiene).
5. **Backend** sembrado en `data/` + `post_init_hook` para migrar credenciales.
6. **Fixtures reales** + pruebas: `tests/fixtures/*.json`, `test_mapping.py` (normalización),
   `test_connector.py` (tolerancia a errores + métricas + circuit breaker), `test_quality.py`.

## Lo que cubre este conector (objetivos D2)
- **Normalización completa** (galería, 360°, documentos, garantía, MAP, stock, SAT, dimensiones) — ver `MAPEO_NORMALIZACION.md`.
- **Fixtures reales** de 10 tipos de producto.
- **Compatibilidad hacia adelante** (campos nuevos → `raw._unknown_keys`, sin romper).
- **Tolerancia a errores**: timeouts, 429, 500, token expirado (refresh+retry), JSON inválido, payload de error, nulos.
- **Métricas por endpoint**: count, avg/max ms, errors, retries, cache hit/miss (`metrics_summary()`).
- **Calidad de datos**: advertencias (SAT, marca, categoría, imagen rota, SKU, precio) + duplicados.
- **IA-ready**: `mapping.to_embedding_text()`.

## Pruebas
`odoo -i distributor_syscom -d <db> --test-enable --test-tags /distributor_syscom`

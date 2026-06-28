# distributor_connector_base — Catalog Engine SDK

SDK **agnóstico al distribuidor** del Motor de Catálogo (proyecto estratégico Alea Systems).
Define el **contrato** que todo conector implementa y la infraestructura común
(resiliencia, eventos, observabilidad, auditoría). **No** contiene lógica de ningún
proveedor concreto.

- **Catalog Engine** `1.0.0` (`lib/version.py`) · módulo Odoo `18.0.1.0.0`
- **Depende de:** `base`

## Qué incluye
- **`lib/`** (Python puro, tipado, testeable sin Odoo):
  - `dto.py` — `NormalizedProduct` (contrato público estable).
  - `connector.py` — `DistributorConnector` (ABC) + **registro** (`@register_connector`).
  - `resilience.py` — `RateLimiter`, `CircuitBreaker`, `backoff_delays` (backoff+jitter), timeouts.
  - `events.py` — `EventBus` + catálogo de eventos.
  - `instrumentation.py` — medición de tiempos.
  - `version.py` — SemVer del motor + compatibilidad.
  - `exceptions.py` — jerarquía `CatalogError`.
- **`models/`** (capa Odoo): `distributor.backend` (config+secretos+rotación), `catalog.run`/`catalog.metric` (observabilidad), `catalog.audit.log` (auditoría append-only), `catalog.event` (eventos persistidos).

## Cómo agregar un distribuidor (resumen)
1. Crear módulo `distributor_<slug>` que dependa de `distributor_connector_base`.
2. Implementar y registrar el conector:
   ```python
   from odoo.addons.distributor_connector_base.lib.connector import (
       DistributorConnector, register_connector)
   from odoo.addons.distributor_connector_base.lib.dto import NormalizedProduct

   @register_connector("miproveedor", requires_engine=">=1.0,<2.0")
   class MiProveedorConnector(DistributorConnector):
       version = "1.0.0"
       def authenticate(self): ...
       def search(self, query, filters=None, page=1): ...   # -> [NormalizedProduct]
       def get_product(self, ref): ...                       # -> NormalizedProduct
       def get_price_stock(self, refs): ...                  # -> {ref: {...}}
       def normalize(self, raw): ...                         # mapea SU JSON -> NormalizedProduct
   ```
3. Crear el registro `distributor.backend` (UI: Motor de Catálogo → Distribuidores) eligiendo el `connector_key`.
4. Añadir `tests/` (unitarios de `normalize()` con fixtures reales). **Sin tocar el núcleo.**

## Pruebas
`odoo -i distributor_connector_base -d <db> --test-enable --test-tags /distributor_connector_base`

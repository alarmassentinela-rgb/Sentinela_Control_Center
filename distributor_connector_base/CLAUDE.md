# distributor_connector_base (Catalog Engine SDK)

SDK del **Motor de Catálogo** (Alea Systems). Capa **agnóstica**: contrato de conectores + infraestructura (resiliencia, eventos, métricas, auditoría). Los conectores concretos (`distributor_syscom`, `distributor_cva`, …) y el motor de orquestación (`product_catalog_engine`) son módulos aparte.

> Documenta **cómo es el código**. El estado/decisiones del proyecto vive en la memoria y en los docs `BLUEPRINT_*`/`CATALOG_ENGINE_STANDARDS_*` del repo raíz.

- **Versión motor:** `lib/version.py::ENGINE_VERSION` (`1.0.0`), independiente del manifest (`18.0.1.0.0`).
- **Depende:** `base`. Odoo 18 Community. DB lab `Sentinela_STAGING` (`odoo-lab` :8075).
- **Deploy:** rsync a `/home/egarza/odoo18-migration/addons/` → `-u/-i` en STAGING. (Aún NO en PROD; el motor arranca solo en STAGING.)

## Arquitectura
- **`lib/` = Python puro, SIN ORM** (importable y testeable aislado). Aquí vive el "framework": DTO, ABC de conector + **registro**, resiliencia (circuit breaker / backoff / rate limiter / timeouts), bus de eventos, instrumentación, versión/compatibilidad, excepciones.
- **`models/` = capa Odoo** que usa `lib`: `distributor.backend` (config por distribuidor R3 + secretos en `ir.config_parameter` R5 + `get_connector()` por registro R4), `catalog.run`+`catalog.metric` (observabilidad R2), `catalog.audit.log` (auditoría append-only R5), `catalog.event` (eventos persistidos R3, puente al `EventBus`).

## Reglas / trampas
- **Extensibilidad por registro, NUNCA `if distributor == 'x'`.** Un conector se registra con `@register_connector(key)`; el backend resuelve por `connector_key`.
- **Secretos**: jamás en columnas del modelo ni en logs; usar `backend.get_secret/set_secret` (→ `ir.config_parameter` `distributor_backend.<id>.<name>`). `rotate_credentials()` invalida el token.
- **`connector_key`** es una Selection **dinámica** (`_sel_connectors`) que lee el registro; con base sola (sin conectores) muestra `(sin conectores instalados)`. Por eso no se crean backends en base pura.
- **`catalog.audit.log`** es append-only: `write()` lanza UserError; `unlink()` solo superuser.
- **lib sin dependencias de Odoo**: no importar `odoo` dentro de `lib/` (rompería su testeo aislado y la portabilidad del motor).
- **Compatibilidad de versión**: `register_connector` valida `requires_engine` contra `ENGINE_VERSION`; incompatibilidad = no se registra (no rompe el motor).

## Pruebas
`tests/test_lib.py` (unitarias lib: versión, dto, eventos, resiliencia, registro) y `tests/test_backend.py` (Odoo: backend/secretos/rotación/conector/run/evento/auditoría). Correr: `--test-enable --test-tags /distributor_connector_base`.

# Mapa de Normalización — Syscom (conector de referencia)

Cómo cada campo de la API de Syscom (`/productos/{id}`) se transforma al `NormalizedProduct`
(DTO del motor) y, posteriormente, al producto de Odoo. **Verificado contra payloads reales**
(fixtures en `tests/fixtures/`).

## Campo API Syscom → NormalizedProduct → Odoo (destino en D4+)

| API Syscom | NormalizedProduct | Odoo (futuro D4) | Transformación / validación |
|---|---|---|---|
| `producto_id` | `external_ref` | `product.supplierinfo.product_code` + `catalog.item.external_ref` | `str()`. Obligatorio; si falta → `NormalizationError`. |
| `titulo` (fallback `modelo`) | `name` | `product.template.name` | Obligatorio (DTO valida). |
| `marca` | `brand` | marca/categoría o atributo | `None` si vacío → warning `no_brand`. |
| `modelo` | `model` | referencia/atributo | — |
| `descripcion` | `description` | `description_sale` | HTML tal cual. |
| `categorias[]` `{nombre,nivel}` | `category_path[]` | `product.category` (jerarquía) | Ordenado por `nivel`; vacío → warning `empty_category`. |
| `precios.precio_descuento` | `price.cost` | `supplierinfo.price` (costo) | `_to_float`; `None` si no parsea. |
| `precios.precio_lista` (fallback `precio_1`) | `price.list` | `list_price` base | `_to_float`. |
| `precios.precio_map` | `price.map` | regla de precio mínimo (R4) | `_to_float`. |
| `precios.precio_especial` | `price.special` | promociones | `_to_float`. |
| (moneda) | `price.currency` = `"USD"` | `res.currency` USD→MXN por TC | Syscom cotiza en USD. |
| `total_existencia` / `existencia.nuevo` | `stock.total` | informativo / reorder | `_to_int`, nunca negativo. |
| `existencia.detalle[]` | `stock.by_warehouse{}` | disponibilidad regional | Lista→dict tolerante. |
| `imagenes[]` `{imagen,orden}` (fallback `img_portada`) | `images[]` (URLs) | `product.image` (URL) | Ordenado por `orden`; **solo URL** (sin binario). |
| `imagen_360` | `image_360` | campo URL | — |
| `recursos[]` `{recurso,path}` | `documents[]` `{name,url,kind}` | `ir.attachment` type=`url` | `kind=datasheet` si "ficha"/"spec" en el nombre. |
| `sat_key` | `sat_key` | `l10n_mx_edi_code_sat` (si vacío) | `str()`; faltante → warning `missing_sat_key`. |
| `unidad_de_medida.clave_unidad_sat` | `sat_unit` | `l10n_mx_edi_um_code_sat` | ej. `H87`. |
| `garantia` | `warranty` | campo propio | texto ("5 años"). |
| `peso` | `weight` | `weight` | `_to_float`. |
| `alto/ancho/largo/pvol` | `dimensions{alto,ancho,largo,volumen}` | volumen/logística | `_to_float`. |
| (payload completo) | `raw.payload` + `raw._unknown_keys` | caché / depuración | **compat. hacia adelante**. |

## Reglas clave
- **Tolerancia a nulos:** todo parseo (`_to_float`, `_to_int`) devuelve `None`/`0` sin lanzar.
- **Compatibilidad hacia adelante:** campos no listados en `KNOWN_KEYS` se registran en `raw._unknown_keys` y **no rompen** la normalización.
- **Payload de error:** Syscom responde **HTTP 200 con `{"error": "..."}`** para productos no disponibles → `is_error_payload()` → `NormalizationError` / `ConnectorError` (no se crea producto).
- **Calidad de datos** (`quality.check`): genera advertencias (`missing_sat_key`, `empty_category`, `no_brand`, `broken_image_url`, `invalid_sku`, `no_price`, `negative_price`) **sin detener** la sincronización; duplicados con `find_duplicates`.
- **IA-ready:** `to_embedding_text(np)` produce el texto canónico (nombre+marca+modelo+categoría+descripción) para generar embeddings/búsqueda semántica más adelante **sin rediseñar** el conector.

## Cobertura de fixtures
`camara_ip`, `nvr`, `switch`, `cable`, `accesorio`, `software`, `servicio`, `sin_imagen`
(detalle real) + `sin_existencia`/`descontinuado_404` (payload de error real). Todos en
`tests/fixtures/`, base de `test_mapping.py` y `test_quality.py`.

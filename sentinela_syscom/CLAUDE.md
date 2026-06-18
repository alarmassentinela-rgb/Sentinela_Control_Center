# sentinela_syscom

Integración con el proveedor/distribuidor **Syscom** (API `developers.syscom.mx`): importa el catálogo de productos, sincroniza precios USD→MXN y stock vía cron nocturno, importa facturas de compra, y depura productos descontinuados. Es un módulo satélite del ecosistema Sentinela en Odoo 18.

> Este archivo se auto-carga al trabajar en el módulo. Documenta el **cómo es el código** (arquitectura, trampas). El **estado/decisiones** del proyecto vive en la memoria (`MEMORY.md`), no aquí. Si cambias algo estructural, actualiza este archivo.

- **Versión actual:** ver `__manifest__.py` (`version`). Hoy `18.0.1.4.0`.
- **Odoo:** 18 Community. **DB prod:** V18 · **DB lab:** Sentinela_STAGING (`odoo-lab` :8075).
- **Deploy:** usar skill `release-modulo` (bump `version` + commit + tag + push) y luego `deploy-modulo` (rsync local→server → `-u` en STAGING → `-u` en V18 → verificar). El server (192.168.3.2) NO es git working tree; **sin rsync el `-u` corre código viejo**.

## Dependencias (manifest)
| Depend | Por qué |
|---|---|
| `base` | `ir.config_parameter` (credenciales Syscom/Telegram), `res.config.settings` |
| `stock` | Productos como inventario; menú raíz cuelga de `stock.menu_stock_root`; `stock.move` para detectar movimiento |
| `product` | Hereda `product.template` y `product.category` (campos `syscom_*`) |
| `purchase` | Hereda `purchase.order`; importa facturas de compra (`in_invoice`) |

## Modelos (models/ y wizard/)
| `_name` / `_inherit` | Archivo | Rol |
|---|---|---|
| `_inherit product.template` (`ProductTemplate`) | `models/product.py` | Campos `syscom_*` (id, modelo, marca, stock, precios USD, descontinuado; **v1.4.0:** `syscom_sat_description`, `syscom_sat_unit_key`, `syscom_caracteristicas` Html, `syscom_datasheet_url`) + helper `_syscom_extract_enrichment(payload)` + cron `_cron_update_syscom_products` |
| `_inherit account.move` (`AccountMove`) | `models/product.py` | Campo `syscom_folio` + `action_sync_syscom_invoices()` (import manual de facturas) |
| `_inherit product.category` (`ProductCategory`) | `models/product_category.py` | Campo `syscom_category_id` (mapeo de jerarquía) |
| `_inherit purchase.order` (`PurchaseOrder`) | `models/purchase_order.py` | Campos `is_syscom_order`, `syscom_order_*`, envíos O2M |
| `sentinela.syscom.shipment` (`SyscomShipment`) | `models/purchase_order.py` | Guías de rastreo de envíos Syscom (datos manuales) |
| `syscom.import.queue` (`SyscomImportQueue`) | `models/syscom_queue.py` | Cola de import por categorías con `process_queue()` — ⚠️ ver Trampas |
| `syscom.import.wizard` (TransientModel) | `wizard/syscom_import_wizard.py` | Importar productos por modelo/marca desde la API |
| `syscom.cleanup.wizard` (TransientModel) | `wizard/syscom_cleanup_wizard.py` | Depurar descontinuados (elimina sin movimiento / archiva con movimiento) |
| `_inherit res.config.settings` | `models/res_config_settings.py` | Credenciales API + Telegram + botón "Test connection" |

## Campos de estado clave
- **`product.template.syscom_discontinued`** (Boolean, indexado) + `syscom_discontinued_date` (Date) — se marca automáticamente en el cron nocturno cuando la API responde 404 o el payload trae `descontinuado: true`. Insumo del wizard de limpieza.
- **`syscom.import.queue.status`** — `pending` / `processing` / `done` / `error`.
- **`purchase.order.syscom_order_status`** — `Pendiente` / `Enviado` / `Entregado` / `Cancelado` (valores en español, solo informativos; la sincronización real no está implementada).

## Crones (data/ir_cron_syscom.xml) — método en models/product.py
| Cron (id) | Método | Cadencia | Qué hace |
|---|---|---|---|
| `ir_cron_syscom_sync` ("Syscom: Update Prices and Stock") | `product.template._cron_update_syscom_products()` | cada 1 día, nextcall 02:00 | OAuth → tipo de cambio (`/tipocambio`, fallback 17.26) → recorre productos con `syscom_id` o `list_price<=1.0` activos y con `default_code`; actualiza `standard_price`, `syscom_stock` + enriquecimiento (`_syscom_extract_enrichment`); **`list_price` SOLO se re-escribe en "rescate" (`list_price<=1.0`)** — v1.4.0, antes lo machacaba siempre; **detecta descontinuados** (404 o flag) y reporta a Telegram. |

**Un solo cron activo.** El cron `Syscom: Sync Order Logistics` fue eliminado en v18.0.1.2.0 (apuntaba a un método inexistente). La detección de descontinuados NO es un cron aparte: ocurre dentro de este mismo cron nocturno.

## Flujos importantes
- **Importación de catálogo (wizard):** `syscom.import.wizard` → `action_search_and_import()` consulta `/productos?busqueda=` y **por cada producto pide la ficha de detalle `/productos/{id}`** (la búsqueda NO trae `descripcion`/`caracteristicas`/`recursos`/`unidad_de_medida`), mapea JSON Syscom → `product.template` (`_import_single_product`), crea/actualiza jerarquía de categorías (`_get_or_create_category`, ordenada por `nivel`, vincula por `syscom_category_id`), descarga imagen **solo al crear** (`img_portada`→`image_1920`), setea `type='consu'` y `l10n_mx_edi_code_sat`.
- **⚠️ Opción B — NO sobre-escribir existentes (v1.4.0):** el match busca por `syscom_id` **O** `default_code` (evita duplicar productos capturados a mano; al matchear por referencia les "pega" el `syscom_id`). Si el producto **ya existe**, `_import_single_product` escribe SOLO los "datos vivos" (`sync_vals`: costo, stock, datos `syscom_*`, enriquecimiento) y **respeta** nombre, `list_price`, `default_code`, categoría e imagen. `list_price` solo se fija si el existente venía `<=1.0` ("rescate"). Solo los productos **nuevos** se crean con todos los campos. Misma regla de `list_price` en el cron.
- **Enriquecimiento de ficha (v1.4.0):** `_syscom_extract_enrichment(payload)` (en `product.template`) saca de la ficha de detalle: `sat_description`, `unidad_de_medida.clave_unidad_sat` (ej. `H87`), `caracteristicas` (lista → `<ul>` HTML escapado) y la ficha técnica (primer `recursos[].path` cuyo `recurso` contenga "ficha"). Lo usan tanto el wizard como el cron. La API de Syscom es **solo de consulta** (catálogo/precios/stock/facturas): NO existen endpoints de carrito/pedidos/listas (404), por eso la compra sigue manual.
- **Precios:** USD desde la API (`precio_descuento`=costo, `precio_lista`=MSRP, `precio_especial`). En el cron: `standard_price = costo*TC`, `list_price = MSRP*TC` (o `costo*TC*1.30` si no hay MSRP). En el wizard: convierte vía tasa de `base.USD` y aplica `list_price = costo*1.30`.
- **Limpieza de descontinuados (wizard):** `syscom.cleanup.wizard` (menú "🧹 Limpiar Descontinuados") clasifica los `syscom_discontinued=True` activos: **archiva** (`active=False`) los que tienen movimiento (`_has_movement`: stock>0, líneas en facturas posted, ventas/compras/stock.move no canceladas) y **elimina** (`unlink`) los que no. Requiere marcar `confirmed`. Fallback: si el `unlink` falla, archiva.
- **Importación de facturas de compra (manual):** `account.move.action_sync_syscom_invoices()` (botón en vista) trae `/facturas`, crea `in_invoice` contra el partner `ref='PROV-SYSCOM'`, evitando duplicados por `syscom_folio`.

## Trampas conocidas
- ⚠️ **`syscom.import.queue` está roto / huérfano:** `process_queue()` llama a `product.template.import_from_syscom_categories(...)` que **no existe en ningún archivo del módulo** → falla siempre. Además **ningún cron** invoca `process_queue` y **no hay entrada en `ir.model.access.csv`** para este modelo. Es código muerto; no usarlo sin implementar el método y los permisos.
- **Órdenes a Syscom no implementadas:** `purchase.order.action_send_to_syscom()` y `action_sync_syscom_status()` lanzan `UserError` a propósito (antes "fingían éxito"; limpiados en v18.0.1.2.0). Los campos `syscom_order_*` y los envíos se capturan a mano.
- **`except: pass` / `except: ...` silenciosos** en el cron (`_cron_update_syscom_products`): errores por producto se cuentan como `errors` pero no se loguean. Telegram es opcional (si no hay token/chat_id, no envía).
- **Tipo de cambio:** el cron tiene fallback hardcoded `tc = 17.26` si `/tipocambio` falla. El wizard hace su propia conversión vía `base.USD.rate` (lógica distinta a la del cron — no comparten función).
- **Credenciales en `ir.config_parameter`** (`sentinela_syscom.client_id/client_secret/api_url/telegram_token/telegram_chat_id`), configurables desde Ajustes. El Telegram fue movido de hardcoded a parámetros en v18.0.1.2.0.
- **El cron también "rescata"** productos con `list_price <= 1.0` aunque no tengan `syscom_id`, buscándolos por `default_code` en la API.

## Wizards / Controllers / Tests
- **Wizards:** `syscom.import.wizard` (importar catálogo) y `syscom.cleanup.wizard` (depurar descontinuados). Vistas en `wizard/*_views.xml`.
- **Controllers:** ninguno.
- **Reports:** ninguno.
- **Tests:** ninguno (no hay carpeta `tests/`).
- **Menús:** raíz "Syscom" bajo Inventario (`stock.menu_stock_root`); item "🧹 Limpiar Descontinuados" → `action_syscom_cleanup_wizard`. El wizard de import se expone vía `action_syscom_import_wizard`.

# D3b — Nacimiento del Producto Maestro (promoción índice → producto)

**Fecha:** 28-jun-2026 · Módulo `product_catalog_engine` · **Solo STAGING.**
Principio rector (#10): **un Producto Maestro existe con independencia del proveedor que lo originó.**

---

## 1. Modelo de promoción
`distributor.catalog.item.promote()` → para cada ítem, `_promote_one()`:
1. **`_find_or_create_master()`** (idempotente, anti-duplicado, multi-proveedor, no-hijack):
   - si el ítem ya tiene `product_tmpl_id` → ese.
   - si ya hay `supplierinfo` de ese distribuidor (mismo `distributor_product_id`) → su maestro.
   - **cross-distribuidor** por `barcode` **solo entre `is_catalog_managed=True`** → enlaza.
   - por `default_code` (= manufacturer SKU) **solo gestionados** → enlaza.
   - si nada coincide → **nace** el `product.template` (`is_catalog_managed=True`).
2. **`_sync_supplierinfo()`** — crea/actualiza el `product.supplierinfo` NATIVO con datos del PROVEEDOR (costo `price`, código `product_code`, distribuidor, `last_sync`).
3. **`_sync_mixed_fields()`** — campos MIXTOS (nombre, descripción) respetando ediciones manuales.
4. **`link_master()`** — enlaza el índice al maestro y AUDITA.

`barcode` se copia al maestro **solo si está libre** (es ÚNICO en Odoo): así no colisiona ni "secuestra" el código de un producto propio.

## 2. Política de OWNERSHIP de datos (regla #4 — sin ambigüedad)
| Propietario | Datos | Dónde viven / regla |
|---|---|---|
| **PROVEEDOR** | costo, existencia, garantía, documentos, ficha técnica, código de distribuidor, plazo | `product.supplierinfo` / `distributor.catalog.item` (**no** en el maestro). El proveedor los actualiza libremente. |
| **ERP** | categoría comercial, impuestos, listas de precios, margen, notas internas, reglas de venta, **relacionados propios** (accessory/alternative), `default_code` | **El proveedor NUNCA los escribe.** (`default_code` se siembra al crear y luego es del ERP.) |
| **MIXTO** | nombre, descripción, imágenes, atributos | El proveedor los pone al promover y **respeta ediciones manuales**: se comparan contra el último valor que el proveedor empujó (`provider_snapshot`); si el usuario lo cambió, NO se sobrescribe. |
Código: `lib/ownership.py` (`PROVIDER_OWNED` / `ERP_OWNED` / `MASTER_MIXED_FIELDS`). Probado: editar el nombre a mano y re-promover → se respeta; tocar `categ_id`/`list_price` → intactos; el costo (proveedor) sí se actualiza.

## 3. Estrategia de conflictos (regla #7)
Si **dos distribuidores** ofrecen el mismo producto, el maestro **permanece único**: el segundo se enlaza por `barcode`/`default_code` (entre gestionados) y se **agrega un `product.supplierinfo`** — **no** se crea un producto nuevo. Odoo elige el mejor proveedor en compras (nativo). Productos **propios** (`is_catalog_managed=False`) **nunca** participan del match → no se secuestran (regla #8).

## 4. Versionado (regla #5)
Cada sincronización deja evidencia en `catalog.audit.log` (no solo precio): **campo, valor anterior, valor nuevo, fecha, origen** (cron/api/wizard/user/system), por cada cambio aplicado al maestro y al supplierinfo.

## 5. SupplierInfo nativo (regla #6)
Se **extiende** `product.supplierinfo` (no se reinventa): costo (`price`), código (`product_code`), plazo (`delay`) nativos + `distributor_backend_id`, `distributor_product_id`, `warranty`, `datasheet_url`, `catalog_item_id`, `last_sync`.

## 6. Evidencia de soporte MULTI-PROVEEDOR (reglas #7/#9)
- **Prueba unitaria** `test_multi_distributor_single_master`: 2 backends, mismo producto → **1 maestro, 2 proveedores**, `distributor_count=2`. ✓
- **Demo en vivo (STAGING):** producto REAL de Syscom (221944) promovido → maestro gestionado, 1 proveedor; un **2º distribuidor ficticio** con el mismo `manufacturer_sku` → **MISMO maestro**, **2 proveedores**, `distributor_count=2`. ✓ (Sin cambios de modelo — regla #9.)

## 7. Independencia del proveedor (criterio de aceptación #10) — DEMOSTRADO
`test_master_independent_of_provider`: se promueve, luego se **elimina el ítem de índice** (simula que el distribuidor borra el producto) → **el `product.template` y su `supplierinfo` siguen existiendo**. El maestro es un **activo del ERP**.

## 8. Benchmark (STAGING)
| Operación | Resultado |
|---|---|
| Crear 1000 ítems de índice | 0.4 s |
| **Promover 1000 (crea 1000 maestros + supplierinfo + auditoría)** | 70.5 s (**~14/s**, ~71 ms c/u) |
| **Re-promover 1000 (idempotente)** | **3.7 s**, masters 1000→1000 (**0 duplicados**) |
| Promoción de producto REAL + multi-proveedor en vivo | OK |
- La promoción masiva (~14/s) es aceptable para uso **bajo demanda** (1 producto al cotizar). Para cargas grandes se optimizará en D3c/D3d con **creación por lotes** y menos búsquedas por ítem. La **re-promoción** (caso recurrente del sync) es rápida.
- Datos de prueba **eliminados** (0 residuos).

## 9. Pruebas
**18 tests, 0 failed, 0 errors** (10 de D3a + 8 de promoción): idempotencia, respeto manual, ownership ERP intacto, multi-proveedor 1 maestro/2 sellers, independencia del proveedor, no-hijack de propios, versionado/auditoría.

## 10. Recomendaciones para D3c (API REST)
- Exponer `/catalog/api/v1`: `search` (índice D3a), `product/{ref}` (detalle vía conector+caché), `promote` (D3b), con auth por API key (Odoo primer consumidor).
- En `promote` por API, registrar `source='api'` (ya soportado por la auditoría).
- Optimizar promoción masiva (lote) antes del scheduler de D3d.
- Mantener el contrato con Membresías: la API del Catálogo **nunca** toca productos propios (`is_catalog_managed=False`).

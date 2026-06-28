# Motor de Catálogo Multi-Distribuidor — Diseño Detallado (v2)

**Fecha:** 28 de junio de 2026 · **Continuación de** `ARQUITECTURA_INTEGRACION_SYSCOM_28JUN2026.md` · **Estado:** diseño previo a aprobación. **No se ha tocado código ni datos.**

> Responde los 9 puntos solicitados, **grounded en el payload real de la API de Syscom** (probado en vivo el 28-jun contra `/productos/{id}`), no en suposiciones.

---

## 1. Diseño agnóstico al proveedor (CVA, CT, Exel, Ingram, Intcomex, Tecnosinergia…)

**Principio:** el núcleo NO conoce a Syscom. Conoce una **interfaz**. Cada distribuidor es un **conector** intercambiable. Añadir un distribuidor = agregar un conector + un registro de configuración. **Cero cambios al núcleo.**

### 1.1 Tres piezas
1. **`distributor.backend`** (modelo de configuración, 1 registro por distribuidor): `name`, `connector_key` (ej. `syscom`), `api_url`, credenciales (en `ir.config_parameter`), `rate_limit`, `currency_id`, `active`, `partner_id` (el proveedor en Odoo). 
2. **`DistributorConnector`** (clase base/interfaz). Cada distribuidor implementa una subclase registrada por `connector_key`:
   ```
   class DistributorConnector(ABC):
       def authenticate() -> token
       def search(query, filters, page) -> [NormalizedItem]      # listado
       def get_product(ref) -> NormalizedProduct                  # detalle
       def get_price_stock(refs) -> {ref: {price, stock, ...}}    # ligero, masivo
       def normalize(raw) -> NormalizedProduct                    # mapea SU JSON → esquema común
   ```
   `SyscomConnector` (hoy), `CVAConnector`, `CTConnector`… cada uno encapsula SU API, SU auth, SU paginación, SU rate-limit.
3. **Esquema normalizado común** (`NormalizedProduct`, dataclass): el resto del sistema **nunca** ve JSON crudo del proveedor. Campos: `ref, name, brand, model, description, category_path[], price{cost,list,map,special,currency}, stock{total,by_warehouse[]}, images[], images_360, docs[], sat_key, sat_unit, dimensions{}, weight, warranty, raw{}`.

### 1.2 Dónde viven los datos del proveedor (clave para multi-distribuidor)
- **`product.supplierinfo` (NATIVO de Odoo)** = "este producto lo ofrece el distribuidor X con código Y, precio Z, plazo W". Odoo ya soporta **varios proveedores por producto** y elige el mejor en compras. **Aquí va el precio/código/stock por distribuidor.** ← esto resuelve de raíz que un mismo producto lo den Syscom + CVA + CT.
- **NUNCA columnas `syscom_*` / `cva_*` / `ct_*`** en `product.template` (acoplan y no escalan). Los campos `syscom_*` actuales se migran a `supplierinfo` + a la capa de índice/caché.

**Resultado:** integrar CVA = crear `distributor.backend(connector_key='cva')` + clase `CVAConnector`. El núcleo (índice, caché, prioridades, historial, promoción, UI) **no se toca**.

---

## 2. Aprovechar el 100% de la API — ¿qué dejamos hoy en la mesa?

**Evidencia (payload real `/productos/{id}`, probado 28-jun en 2 productos):**

| Dato de la API | ¿La API lo da? | ¿Lo capturamos hoy? | Acción propuesta |
|---|---|---|---|
| `img_portada` | ✅ | ✅ (solo al crear) | mantener |
| **`imagenes` (galería, n=5)** | ✅ | ❌ | importar como galería (`product.image`) — **solo URLs** |
| **`imagen_360`** | ✅ | ❌ | guardar URL |
| **`iconos`** (sup_izq/der, inf_der) | ✅ | ❌ | opcional (badges) |
| **`recursos` (TODOS los documentos)** | ✅ | ⚠️ solo el 1.º "ficha" | importar **todos** como adjuntos-URL |
| **`garantia`** ("5 años") | ✅ | ❌ | nuevo campo |
| `precios.precio_descuento/lista/especial` | ✅ | ✅ | mantener |
| **`precios.precio_map`** (precio mínimo anunciado) | ✅ | ❌ | nuevo campo (clave para política de precio) |
| `total_existencia` | ✅ | ✅ | mantener |
| **`existencia.detalle`** (stock **por almacén**) | ✅ | ❌ | capturar (disponibilidad regional) |
| **dimensiones** `alto/ancho/largo/pvol` | ✅ | ⚠️ solo `peso` | capturar (logística/envíos) |
| `sat_key`, `sat_description`, `unidad_de_medida` | ✅ | ✅ | mantener |
| `categorias_producto_todas` (ruta completa) | ✅ | ⚠️ parcial | mapear ruta completa |
| `marca`, **`marca_logo`** | ✅ | ⚠️ marca sí, logo no | logo opcional |
| **Accesorios** | ❌ **NO existe en el endpoint** | — | **no se puede importar**; mantener manual en Odoo (`accessory_product_ids`) |
| **Productos relacionados** | ❌ **NO existe** | — | manual (`alternative_product_ids`) |
| **Videos** | ❌ **NO existe** | — | manual si se quiere |
| **Compatibilidades** | ❌ **NO existe** | — | manual / no disponible |

> **Hallazgo importante y honesto:** la API de Syscom **NO entrega accesorios, relacionados, videos ni compatibilidades** (verificado en vivo). No prometamos importarlos: o se capturan **manualmente** en Odoo (que aporta venta cruzada con los campos nativos) o se obtienen de otra fuente. Lo que **sí** estamos desperdiciando y vale oro: **galería de imágenes, 360°, TODOS los documentos, garantía, precio MAP, stock por almacén y dimensiones.**

El **conector** define qué campos mapea; si un distribuidor da más (p. ej. CVA con fichas o compatibilidades), su `normalize()` los llena y el núcleo los aprovecha sin cambios.

---

## 3. Caché local de productos consultados recientemente

**Sí, conviene** — reduce llamadas a la API y da respuesta instantánea sin sacrificar frescura, con TTL por tipo de dato.

- Modelo **`distributor.catalog.cache`** (o el propio índice con campos `last_fetched_*`): guarda el `NormalizedProduct` (JSON normalizado) + timestamps por bloque.
- **TTL diferenciado:** stock 1-4 h · precio 12-24 h · enriquecimiento (imágenes/ficha/garantía) 7-30 días.
- Flujo: al consultar un producto (búsqueda/cotización), si la caché está **fresca** → se sirve de caché; si está **vencida** → se refresca de la API y se re-cachea. 
- Beneficio: si 5 vendedores consultan la misma cámara en una hora, **1 llamada** a la API, no 5. Respeta el rate-limit y acelera la UI.

---

## 4. Sistema de prioridades de sincronización (por uso real)

No todo se actualiza igual. Cada producto recibe un **`sync_tier`** calculado por uso:

| Tier | Criterio | Precio | Stock | Enriquecimiento |
|---|---|---|---|---|
| **0 — Caliente** | en **cotizaciones/OC abiertas**, favoritos/kits, compra últimos 7 d | en vivo / cada 1-2 h | **en vivo al cotizar** + cada 1-2 h | al promover |
| **1 — Activo** | vendido/facturado últimos 90 d, con stock | diario | cada 4 h | semanal |
| **2 — Propio inactivo** | en Odoo pero sin movimiento reciente | semanal | bajo demanda | mensual |
| **3 — Catálogo** | en el índice, NO almacenado como producto | — | bajo demanda (caché) | al promover |

- El `sync_tier` se recalcula con un cron ligero (lee ventas/compras/cotizaciones/favoritos) y **dirige qué lote toca cada cron**. Así el cron nunca recorre "todo": recorre **Tier 0/1** (decenas/cientos), Tier 2 espaciado, Tier 3 nunca de forma programada.
- "Favoritos" = lista curada por compras (productos estrella). Se puede marcar a mano o derivar de top-ventas.

---

## 5. Historial de precios del proveedor

**Modelo `distributor.price.history`** (append-only, solo cuando cambia):
- Campos: `product_id`, `backend_id` (distribuidor), `date`, `cost_usd`, `list_usd`, `map_usd`, `fx_rate`, `cost_mxn`, `source` (cron/wizard).
- Se inserta un renglón **solo si el precio cambió** respecto al último (ligero; no crece sin control).
- Habilita: **tendencias de costo**, **análisis de margen** (vs precio de venta), alertas "subió X%", comparativa **entre distribuidores** del mismo SKU a lo largo del tiempo.
- Complementa (no reemplaza) el tracking de `mail.thread`; un modelo dedicado es mucho mejor para reportes/BI.

---

## 6. Índice ligero del catálogo vs tiempo real

**Recomendación: AMBOS, en capas** (es el punto óptimo).

- **Índice ligero `distributor.catalog.item`** (metadatos, **sin binarios**): `backend_id, ref, name, brand, category_path, price_list, stock_total, sat_key, thumb_url, last_seen`. Permite **buscar/navegar TODO el catálogo dentro de Odoo** (rápido, indexable) sin inflar `product.template` ni guardar imágenes.
  - Se alimenta por **delta/semanal** (o por páginas espaciadas) y por **caché al consultar**.
- **Tiempo real** para el dato **crítico al decidir**: al meter un producto a cotización/OC, se consulta **stock y precio en vivo** (autoritativo).

**Por qué ambos:** el índice da *descubrimiento* (encontrar cualquier SKU sin salir de Odoo); el tiempo real da *exactitud* en el momento que importa (cotizar/comprar). Solo-tiempo-real pierde navegación/offline; solo-índice arriesga cotizar con datos viejos. La capa combinada resuelve los dos.

---

## 7. Política de imágenes y documentos

**Preferir URL/CDN del proveedor; almacenar binario solo cuando aporta.**

| Enfoque | Ventajas | Riesgos | Mitigación |
|---|---|---|---|
| **URL/CDN** (recomendado por defecto) | ~0 almacenamiento; siempre la versión del proveedor; respaldos ligeros | el link puede **caducar/cambiar** (link-rot); depende de la disponibilidad del CDN; posible *hotlinking* bloqueado; peticiones externas en la UI | **chequeo de salud de links** periódico; refrescar URL en el siguiente sync; *fallback* a placeholder |
| **Binario local** (selectivo) | offline, control total, sin dependencia externa | **peso** (hoy 7.6 GB), respaldos pesados | **solo** imagen principal de productos **publicados/en uso**; a futuro, almacenamiento de objetos (S3/MinIO) |

**Regla práctica:**
- **Productos en uso/publicados:** cachear **la imagen principal** localmente (pequeña) + galería y documentos **como URL**.
- **Catálogo (índice):** **todo por URL** (thumb_url), cero binarios.
- **Documentos/fichas:** **siempre URL** al CDN de Syscom; archivar PDF local solo si hay requisito de conservación.

Esto evita repetir el problema de los 7.6 GB y mantiene el catálogo navegable con imágenes.

---

## 8. ¿Módulo como "Motor de Catálogo" independiente del ERP?

**Sí — ese es el diseño objetivo.** Separar en:

- **`product_catalog_engine`** (núcleo agnóstico): registro de conectores, esquema normalizado, índice, caché, prioridades, historial de precios, *scheduler* de sync, **promoción** (índice→`product.template`), y la UI de búsqueda/navegación. **No conoce a Syscom.**
- **Conectores delgados** (un paquete por distribuidor): `catalog_connector_syscom`, `catalog_connector_cva`, `catalog_connector_ct`… Cada uno **solo** implementa `DistributorConnector` y trae su `distributor.backend`.

Syscom pasa a ser **un conector más**. Ventajas: reutilizable, **testeable por conector**, aislado (un cambio en la API de CVA no afecta a Syscom), y portable (mañana podría exponerse como microservicio si se quisiera, pero **dentro de Odoo como módulo limpio es el objetivo pragmático**).

---

## 9. Diagrama de arquitectura

### 9.1 Modelo de datos
```
                         ┌──────────────────────────────┐
                         │        product.template       │  (SOLO productos en uso)
                         │  name, sat_key, image (princ),│
                         │  accessory_product_ids,       │  ← accesorios/relacionados MANUAL
                         │  alternative_product_ids      │
                         └───────┬───────────────▲───────┘
                  1..N supplierinfo│             │ promueve (índice→producto)
                         ┌─────────▼─────────┐   │
                         │ product.supplierinfo│  │   ┌───────────────────────────┐
                         │ partner=distribuidor│  │   │ distributor.price.history │
                         │ code, price, delay  │──┼──▶│ date, cost_usd, map, fx,  │
                         └─────────▲───────────┘  │   │ cost_mxn  (append on change)│
                                   │              │   └───────────────────────────┘
   ┌───────────────────────┐      │       ┌──────┴────────────────────┐
   │  distributor.backend  │      │       │  distributor.catalog.item │  (índice ligero,
   │  connector_key, api,  │      │       │  ref,name,brand,cat,price,│   sin binarios)
   │  creds, rate, active  │──────┼──────▶│  stock,thumb_url,sync_tier│
   └───────────┬───────────┘      │       │  + cache JSON + last_fetch│
               │ usa              │       └───────────────────────────┘
   ┌───────────▼─────────────────────────────────────────┐
   │   DistributorConnector (interfaz)  →  NormalizedProduct│
   │   ├─ SyscomConnector   ├─ CVAConnector  ├─ CTConnector │
   └───────────────────────────────────────────────────────┘
```

### 9.2 Flujo de sincronización y consulta
```
  (A) DESCUBRIR / NAVEGAR
      Usuario busca → índice local (rápido)  ──miss/vencido──▶ Connector.search() → cachea
                                   │ hit fresco
                                   ▼  muestra resultados (índice)

  (B) COTIZAR / COMPRAR  (dato crítico = en vivo)
      Agregar producto → Connector.get_price_stock(ref)  → precio+stock AUTORITATIVO
                       → si no existe como product.template → PROMOVER:
                          Connector.get_product(ref) → NormalizedProduct
                          → crea product.template + supplierinfo + imágenes(URL)+docs(URL)
                          → registra precio en price.history

  (C) SYNC PROGRAMADO  (por prioridad, NUNCA "todo")
      cron FX (1/día) ─┐
      cron precio  ────┼─▶ recorre SOLO Tier 0/1 (cientos) → supplierinfo + price.history
      cron stock   ────┘   Tier 0/1 (1-4 h);  Tier 2 espaciado;  Tier 3 jamás programado
      cron tier (1/día) → recalcula sync_tier desde ventas/cotizaciones/compras/favoritos
      cron índice (semanal/delta) → refresca distributor.catalog.item (metadatos)
```

---

## 10. Riesgos identificados (¿hay alguno que frene la aprobación?)

| Riesgo | Severidad | Mitigación | ¿Bloqueante? |
|---|---|---|---|
| API Syscom **no da** accesorios/relacionados/videos/compatibilidades | 🟡 Bajo | mantener manual en Odoo (campos nativos) | No |
| **Link-rot** de imágenes/docs por URL del CDN | 🟡 Bajo-medio | chequeo de salud + refresco en sync; imagen principal local en publicados | No |
| Stock en vivo al cotizar **depende de la API** | 🟡 Bajo | *fallback* a caché con aviso "dato de hace X"; rate-limit ya resuelto | No |
| Refactor a `supplierinfo` + conector (Fase 4) | 🟠 Medio | por fases, en STAGING, con pruebas; Fases 1-2 dan valor sin el refactor | No |
| Migrar datos `syscom_*` existentes | 🟡 Bajo | script de migración reversible; lista blanca de 36+67 productos | No |

**Conclusión: no hay riesgos bloqueantes.** Todos tienen mitigación conocida. La arquitectura es estándar de ERP, agnóstica y escalable a N distribuidores.

---

## 11. Cómo encaja con el plan por fases (v1)
El plan de 6 fases del documento v1 **no cambia**, se enriquece:
- **Fase 1-2** (limpieza + cron escalable) siguen siendo el arranque de mayor valor inmediato.
- Este diseño v2 detalla **Fase 3** (enriquecimiento: galería/docs/garantía/MAP/stock-por-almacén + caché + historial de precios + prioridades) y **Fase 4** (`product_catalog_engine` + conectores + `supplierinfo`), y agrega **Fase 5** (índice ligero) ya con modelo de datos definido.

> **Arranque acordado: SOLO STAGING.** Ninguna limpieza/eliminación en producción hasta validar la nueva arquitectura end-to-end en STAGING y medir impacto (tiempos de cron, peso de DB/filestore, frescura de precio/stock). Producción se toca solo tras tu visto bueno con métricas en mano.

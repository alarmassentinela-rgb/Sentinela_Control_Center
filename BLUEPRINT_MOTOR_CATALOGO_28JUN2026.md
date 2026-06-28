# BLUEPRINT — Motor de Catálogo Multi-Distribuidor (arquitectura definitiva)

**Fecha:** 28 de junio de 2026 · **Documento maestro** del proyecto · **Reemplaza conceptualmente** la idea de "integración con Syscom": Syscom pasa a ser **un conector más** del Motor de Catálogo del ERP.
**Precedentes:** `ARQUITECTURA_INTEGRACION_SYSCOM_28JUN2026.md` (diagnóstico) · `ARQUITECTURA_SYSCOM_V2_DISENO_28JUN2026.md` (diseño v2).
**Estado:** blueprint para aprobación. **No se ha tocado código ni datos.** El desarrollo arranca **solo en STAGING** una vez aprobado.

---

## 0. Visión

Un **Motor de Catálogo** propio del ERP que:
- mantiene **nuestros** productos (los que se transaccionan) limpios y enriquecidos,
- consulta el catálogo de **cualquier distribuidor** bajo demanda mediante **conectores intercambiables**,
- es **agnóstico al proveedor**: agregar CVA / CT / Ingram / Exel / Intcomex / Tecnosinergia = **escribir solo un conector**, sin tocar el núcleo,
- **extiende** Odoo (no lo reemplaza): se apoya en `product.supplierinfo`, `product.image`, `ir.attachment(url)`, compras/ventas nativas.

---

## 1. Estructura final de módulos

### 1.1 Capas
```
  NÚCLEO (agnóstico)                         CONECTORES (1 por distribuidor)
  ┌───────────────────────────┐             ┌───────────────────────┐
  │ distributor_connector_base│◀────────────│ distributor_syscom    │
  │  (el "SDK" de conectores) │   implementa│ distributor_cva       │
  └─────────────▲─────────────┘             │ distributor_ct        │
                │ usa el contrato           │ distributor_ingram    │
  ┌─────────────┴─────────────┐             │ distributor_exel      │
  │ product_catalog_engine    │             │ distributor_intcomex  │
  │  (índice, caché, sync,    │             │ distributor_tecnosi…  │
  │   precios, promoción, UI) │             └───────────────────────┘
  └───────────────────────────┘
```

### 1.2 Módulos, responsabilidad y dependencias
| Módulo | Responsabilidad | Depende de |
|---|---|---|
| **`distributor_connector_base`** | **Contrato/SDK**: clase abstracta `DistributorConnector`, dataclass `NormalizedProduct`, modelo `distributor.backend`, **registro** de conectores por `connector_key`, utilidades HTTP comunes (Session+Retry, rate-limiter, caché de token, normalizador de errores). **Sin lógica de negocio ni UI.** | `base`, `product`, `mail` |
| **`product_catalog_engine`** | **El motor**: índice `distributor.catalog.item`, **caché** con TTL, `distributor.price.history`, **prioridades/`sync_tier`** + *scheduler*, **promoción** (índice→producto), enriquecimiento (galería/docs/garantía/MAP/stock-por-almacén), pegado a `product.supplierinfo`, **UI de búsqueda/navegación**, chequeo de salud de links. | `distributor_connector_base`, `product`, `stock`, `purchase`, `uom` |
| **`distributor_syscom`** | Conector Syscom: auth, endpoints `/productos`, paginación, rate-limit propio, `normalize()` (mapea su JSON → `NormalizedProduct`), su `distributor.backend` semilla. | `distributor_connector_base` |
| **`distributor_cva`**, **`_ct`**, **`_ingram`**, **`_exel`**, **`_intcomex`**, **`_tecnosinergia`** | Un conector cada uno (mismo patrón que Syscom). | `distributor_connector_base` |
| *(consumidores existentes)* `sentinela_subscriptions`, `sentinela_syscom`* | No cambian su API pública; consumen productos como hoy. *(`sentinela_syscom` se adelgaza: su parte de catálogo migra al motor; conserva import de facturas de compra / envíos hasta moverlos.) | `product` |

> **Regla de oro:** el núcleo **no importa** ningún módulo de conector. Los descubre en tiempo de ejecución por el **registro** (`connector_key` del `distributor.backend` → clase registrada por el conector instalado). Quitar un conector = desinstalar su módulo; el núcleo sigue.

### 1.3 ¿Construir el SDK o usar OCA?
- **Recomendado:** SDK propio **delgado** (`distributor_connector_base`) + **OCA `queue_job`** para asincronía a escala (importaciones/sincronizaciones en segundo plano, reintentos). Control total, simple, sin sobre-ingeniería.
- **Alternativa:** OCA **`connector`** framework (backend/binding/jobs) — potente y probado, pero pesado y con curva de aprendizaje. Si a futuro hay muchísimos conectores/volumen, se evalúa migrar el SDK propio a ese patrón. *(Decisión documentada; arrancamos con SDK propio + queue_job.)*

---

## 2. Modelo de datos (ERD)

### 2.1 Qué pertenece al **producto maestro** vs al **distribuidor**
- **Producto maestro (`product.template`/`product.product`, NATIVO):** identidad e info **nuestra** e independiente del proveedor → nombre, referencia interna, **clave SAT** (`l10n_mx_edi_code_sat`), UoM, categoría en **nuestro** árbol, imagen principal, **accesorios/alternativos** (manuales), precio de venta. *Sin columnas por-distribuidor.*
- **Por distribuidor (multi-vendor):** código externo, **costo / lista / MAP**, stock, moneda, plazo, enriquecimiento crudo, **historial de precios** → en `product.supplierinfo` (nativo) + `distributor.catalog.item` + `distributor.price.history`.

### 2.2 Tablas nuevas y relaciones
```
 ┌───────────────────────────┐
 │  distributor.backend      │   (1 por distribuidor)
 │  id, name, connector_key  │
 │  partner_id → res.partner │───────────────┐
 │  api_url, currency_id,    │               │ 1
 │  rate_limit, active       │               │
 └─────────────▲─────────────┘               │
        backend │ N                          │ N
 ┌──────────────┴──────────────┐   ┌─────────▼───────────────────────┐
 │ distributor.catalog.item    │   │ product.supplierinfo (NATIVO,ext)│
 │ id, backend_id, external_ref│   │ partner_id (=distribuidor)       │
 │ name, brand, model,         │   │ product_tmpl_id → product.template│
 │ category_path,              │   │ product_code (=external_ref)     │
 │ price_list, price_cost,     │   │ price, currency_id, delay,min_qty│
 │ price_map, currency,        │   │ + catalog_item_id, last_sync     │
 │ stock_total, stock_json,    │   └─────────▲────────────────────────┘
 │ sat_key, thumb_url,         │             │ N
 │ sync_tier, last_seen,       │             │ 1
 │ last_fetch_price/stock/enr, │   ┌─────────┴───────────────────────┐
 │ raw_json (CACHÉ),           │   │  product.template (NATIVO)       │
 │ product_tmpl_id (nullable)  │──▶│  name, l10n_mx_edi_code_sat, uom,│
 └─────────────▲───────────────┘ 0/1│ image_1920, image_ids(galería),│
        item   │ N                  │  accessory_product_ids,         │
 ┌─────────────┴───────────────┐   │  alternative_product_ids,       │
 │ distributor.price.history   │   │  attachment(url) = documentos   │
 │ id, backend_id, external_ref│   └─────────────────────────────────┘
 │ product_tmpl_id (nullable), │
 │ date, cost_usd, list_usd,   │   Galería  → product.image (campo url externo)
 │ map_usd, fx_rate, cost_mxn, │   Documentos→ ir.attachment type='url' (sin binario)
 │ source (cron/wizard/api)    │   Garantía → campo en product.template o catalog.item
 └─────────────────────────────┘
```

### 2.3 Índices clave
- `distributor.catalog.item`: **UNIQUE (backend_id, external_ref)**; índice en `product_tmpl_id`, `sync_tier`, `brand`; **GIN/pg_trgm en `name` y un `code_norm`** (código normalizado sin guiones → resuelve "pro-cat-5e" ↔ "procat5e").
- `product.supplierinfo`: índice (product_tmpl_id, partner_id) — nativo.
- `distributor.price.history`: índice (backend_id, external_ref, date).

### 2.4 Notas
- `raw_json` en `catalog.item` = **caché** del `NormalizedProduct` + `last_fetch_*` por bloque (precio/stock/enriquecimiento) para los **TTL diferenciados**.
- **Cero binarios** en `catalog.item` (solo `thumb_url`). Imágenes/documentos como **URL** (ver §6/§política v2).

---

## 3. Flujo completo (búsqueda → venta)

```
 1) BÚSQUEDA            Usuario busca "domo hikvision"
                        → engine.search() consulta el ÍNDICE local (rápido, trgm)
                          ├─ hay resultados frescos → los muestra
                          └─ índice pobre/vencido → Connector.search() (API) → cachea en índice

 2) CACHÉ              Al abrir un resultado: si raw_json fresco (TTL) → de caché;
                        si vencido → Connector.get_product(ref) → re-cachea

 3) CONSULTA API       Stock/precio "del momento": Connector.get_price_stock(ref)
                        (autoritativo; respeta rate-limit; cae a caché con aviso si la API falla)

 4) IMPORTACIÓN        Decisión de transaccionar → engine.promote(catalog_item):
   (promoción)           crea/liga product.template (identidad+SAT+UoM)
                         + product.supplierinfo (distribuidor, código, costo, plazo)
                         + galería(URLs)+documentos(URLs)+garantía+dimensiones
                         + registra precio en price.history

 5) COMPRA             purchase.order NATIVO → Odoo sugiere proveedor por supplierinfo
                        (si varios distribuidores, elige el mejor costo/plazo)
                        → recepción → stock real en Odoo

 6) VENTA              sale.order NATIVO → precio de venta de Odoo; accesorios/alternativos
                        sugieren venta cruzada → factura/CFDI (módulos actuales)

 7) ACTUALIZAR PRECIOS cron por TIER: FX 1/día; precio Tier0/1 1/día → supplierinfo
                        + price.history (solo si cambió)

 8) ACTUALIZAR STOCK   Tier0 en vivo al cotizar + cada 1-2h; Tier1 cada 4h;
                        Tier2 bajo demanda; Tier3 nunca programado (solo caché al consultar)

 9) MANTENIMIENTO      cron tier (1/día) recalcula sync_tier desde ventas/cotizaciones/compras/favoritos
                        cron índice (semanal/delta) refresca catalog.item
                        cron link-health revisa URLs de imágenes/docs
```

---

## 4. Roadmap por entregables (pequeños, independientes, reversibles)

> **Regla:** cada entregable deja el sistema **funcionando** y es **reversible**. Todo en **STAGING** hasta validar. Nada destructivo en PROD sin métricas + visto bueno.

| # | Entregable | Qué entrega | Reversibilidad |
|---|---|---|---|
| **D0** | **Línea base** | Backup DB+filestore; medir (peso, tiempos cron, frescura); exportar lista blanca (36 con uso + 67 manuales). | N/A (no cambia nada) |
| **D1** | `distributor_connector_base` | SDK instalado: ABC, `NormalizedProduct`, `distributor.backend`, registro, utils HTTP. **Sin efecto operativo.** | Desinstalar módulo |
| **D2** | `distributor_syscom` (solo lectura) | Conector que envuelve la API actual y devuelve `NormalizedProduct`. **El cron viejo sigue igual.** Validación: `get_product`/`search`/`price_stock` correctos. | Desinstalar; cron viejo intacto |
| **D3** | `product_catalog_engine` — índice + búsqueda | `catalog.item` poblado para Syscom (metadatos, sin binarios) + UI de búsqueda/navegación. **No toca `product.template`.** | Vaciar índice / desinstalar |
| **D4** | Promoción + enriquecimiento bajo demanda | Wizard de alta usa el motor: trae galería/docs/garantía/MAP/stock-por-almacén (URLs). Caché con TTL. | Aditivo; revertir wizard al anterior |
| **D5** | Tiers + nuevo scheduler (sombra) | Cron nuevo refresca **solo Tier0/1** (vía supplierinfo). Corre **en paralelo** al viejo en STAGING y se **comparan** resultados; luego se apaga el viejo. | Reactivar cron viejo (toggle del panel) |
| **D6** | Historial de precios | `price.history` + captura al refrescar (solo cambios). | Aditivo; borrar tabla |
| **D7** | Migración de datos | Script `syscom_*` → `supplierinfo` + `catalog.item` (idempotente, con backup). | Restaurar backup; campos viejos intactos hasta confirmar |
| **D8** | Limpieza + recuperación de espacio | Archivar/eliminar no usados; imágenes→URL; **recupera ~7.6 GB**. **STAGING, medir, luego PROD con visto bueno.** | Restaurar backup D0 |
| **D9** | 2.º conector (CVA) | `distributor_cva` como prueba de agnosticismo: catálogo CVA en el mismo motor, comparando precios con Syscom en `supplierinfo`. | Desinstalar conector |

---

## 5. Núcleo vs Conector (frontera estricta)

| Capacidad | Núcleo (`engine`/`base`) | Conector (por distribuidor) |
|---|---|---|
| Esquema `NormalizedProduct` | ✅ define | consume |
| Autenticación / token | utils comunes | ✅ **implementa** (su OAuth/keys) |
| Endpoints, paginación, parámetros | — | ✅ **implementa** |
| Rate-limit / Retry | utils comunes | ✅ **configura** sus límites |
| **`normalize(raw)→NormalizedProduct`** | contrato | ✅ **implementa** (mapea SU JSON) |
| Mapeo de errores del proveedor | contrato | ✅ **implementa** |
| Índice, caché, TTL | ✅ | — |
| Prioridades / `sync_tier` / scheduler | ✅ | — |
| Promoción a `product.template` + `supplierinfo` | ✅ | — |
| Historial de precios | ✅ | — |
| UI búsqueda/navegación/promoción | ✅ | — |
| Galería/documentos (URL), garantía, dimensiones | ✅ (almacena) | ✅ (los provee si su API los da) |

> **Criterio de éxito del diseño:** agregar un distribuidor = **un módulo `distributor_xxx`** que implementa `authenticate / search / get_product / get_price_stock / normalize` + su `distributor.backend`. **Cero cambios** en `engine` y `base`.

---

## 6. Máximo aprovechamiento de Odoo nativo (extender, no reemplazar)

| Necesidad | Nativo de Odoo a usar | Qué NO construimos |
|---|---|---|
| Precio/código/plazo por proveedor, **multi-vendor** | **`product.supplierinfo`** | tabla propia de precios por proveedor |
| Selección de mejor proveedor en compra | **`purchase`** (sugerencia por supplierinfo) | lógica propia de "mejor precio" |
| Galería de imágenes | **`product.image` / `image_ids`** (+ campo URL) | almacén de imágenes propio |
| Documentos/fichas | **`ir.attachment` `type='url'`** | guardar PDFs binarios |
| Venta cruzada | **`accessory_product_ids` / `alternative_product_ids` / `optional_product_ids`** | módulo de "relacionados" propio |
| Categorías / UoM | **`product.category` / `uom.uom`** | jerarquía propia |
| Tipo de cambio | **`res.currency` + rates** | FX propio (solo lo alimentamos) |
| Programación | **`ir.cron`** (+ OCA **`queue_job`** para asíncrono) | scheduler propio |
| Búsqueda difusa (guiones) | **pg_trgm** + campo `code_norm` + `name_search` | motor de búsqueda externo |
| Trazabilidad/log | **`mail.thread` / activity** | bitácora propia |
| Configuración | **`ir.config_parameter` / `res.config.settings`** | tabla de settings propia |
| UI de listas/kanban/filtros del índice | **vistas estándar** sobre `catalog.item` | front-end propio/JS |

---

## 7. Migración gradual (patrón *strangler-fig*, con rollback por etapa)

**Idea:** construir lo nuevo **al lado** de lo viejo, enrutar de a poco, mantener lo viejo como red de seguridad, conmutar, y **al final** desmantelar.

1. **Coexistencia (D1-D4):** el motor y el conector se instalan y **conviven** con `sentinela_syscom` actual. El cron viejo **sigue mandando** hasta D5. Si algo falla, se desinstala lo nuevo sin tocar producción.
2. **Sombra y comparación (D5):** el cron nuevo corre **en paralelo** en STAGING; comparamos precios/stock/tiempos contra el viejo. Solo cuando coinciden y mejora, se **apaga el viejo** (toggle del panel — reversible al instante).
3. **Migración de datos (D7):** script **idempotente** `syscom_*`→`supplierinfo`/`catalog.item`, conservando los campos viejos hasta confirmar. Rollback = restaurar backup; los campos viejos siguen ahí.
4. **Limpieza (D8):** **lo último** y solo tras validar todo. STAGING → medir → PROD con visto bouno. Rollback = backup D0.
5. **Desmantelar (post-D9):** una vez estable, adelgazar/retirar la parte de catálogo de `sentinela_syscom` (su import de compras/envíos se mantiene o se mueve a `distributor_syscom`).

**Operación diaria intacta:** en ningún paso previo a D8 se borra o se cambia el comportamiento de ventas/compras; lo nuevo es **aditivo** hasta el corte controlado.

---

## 8. Riesgos y criterios de aceptación por fase

### 8.1 Riesgos técnicos
| Riesgo | Mitigación |
|---|---|
| API del proveedor sin algunos datos (accesorios/relacionados/videos en Syscom) | manuales en Odoo; el conector llena lo que su API sí da |
| **Link-rot** de imágenes/docs (URL del CDN) | chequeo de salud + refresco en sync; imagen principal local en publicados |
| Stock en vivo depende de la API | *fallback* a caché con aviso de antigüedad; rate-limit ya resuelto |
| Búsqueda con guiones/normalización de códigos | `code_norm` + pg_trgm |
| Registro de conectores / colisión de `connector_key` | validación única + tests por conector |
| `queue_job`/cron a escala | lotes + idempotencia + commits por tanda |

### 8.2 Riesgos operativos
| Riesgo | Mitigación |
|---|---|
| Borrar algo en uso | lista blanca (movimiento/stock/facturas) + backup + STAGING primero |
| Cotizar con precio/stock viejo durante transición | cron sombra + comparación antes del corte |
| Curva de aprendizaje del equipo | UI nativa; documentar; el manual de Ajustes ya existe |
| Dependencia de un dev para nuevos conectores | el SDK + un conector de ejemplo (Syscom) como plantilla |

### 8.3 Criterios de aceptación (gate) por entregable
| # | Se aprueba pasar a la siguiente fase si… |
|---|---|
| **D0** | Backup restaurable verificado; métricas base capturadas. |
| **D1** | Módulo instala/desinstala limpio; tests del contrato verdes; sin efecto en operación. |
| **D2** | `get_product/search/price_stock` devuelven datos correctos vs la web de Syscom en ≥20 SKUs de muestra. |
| **D3** | Índice poblado; búsqueda < 1 s; **`product.template` sin cambios**; sin binarios en el índice. |
| **D4** | Promoción crea producto con SAT/UoM/galería(URL)/docs(URL)/garantía/MAP correctos; caché respeta TTL. |
| **D5** | Cron nuevo termina **en segundos**; precios/stock de Tier0/1 coinciden con el viejo en ≥99%; viejo apagado sin incidencias. |
| **D6** | `price.history` registra solo cambios; reporte de tendencia/margen funciona. |
| **D7** | 100% de productos en uso con `supplierinfo` Syscom correcto; conteos cuadran; rollback probado. |
| **D8** | En STAGING: filestore/DB reducidos según meta (~7.6 GB liberados), ventas/compras/facturas íntegras; **solo entonces** PROD. |
| **D9** | Alta de CVA **sin tocar** `engine`/`base`; comparación de precios Syscom vs CVA visible en `supplierinfo`. |

---

## 9. Decisión y siguiente paso
- **Recomendación:** aprobar este blueprint y arrancar **D0→D3 en STAGING** (línea base + SDK + conector Syscom de lectura + índice/búsqueda). Es 100% aditivo y reversible, y ya demuestra el motor sin tocar nada de producción.
- **Compromiso:** ninguna limpieza/eliminación ni cambio de comportamiento en PROD hasta superar D5 (cron sombra validado) y, para D8, presentar métricas y obtener visto bueno explícito.

> **Apéndice — Fuentes de los datos técnicos:** payload real `/productos/{id}` (probado 28-jun, IDs 377 y 221944), métricas SQL de `Sentinela_V18`, código `sentinela_syscom` (cron 3 fases, wizard, settings), y los documentos v1/v2 citados.

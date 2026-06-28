# Arquitectura de la Integración con Syscom — Revisión y Propuesta

**Fecha:** 28 de junio de 2026 · **Autor:** Claude (Opus 4.8) para Enrique Garza · **Alcance:** `sentinela_syscom` (Odoo 18 Community, DB `Sentinela_V18`)

> Documento de arquitectura solicitado: diagnóstico, problemas, riesgos, alternativas, recomendación, plan por fases e impacto. **No se ha modificado código ni borrado producto alguno** — esto es análisis previo a decidir.

---

## 0. Resumen ejecutivo (TL;DR)

Hoy estamos **espejando casi todo el catálogo de Syscom** dentro de Odoo: **46,843 productos**, **980 categorías**, **~7.6 GB de imágenes**. De todo eso, **solo 36 productos tienen movimiento real** (venta/compra/factura/inventario) y **0 tienen stock**. El cron nocturno **ya no termina** (timeout a los ~63 min) porque intenta mantener 47 mil fichas cada noche.

**El problema no es el cron: es la estrategia.** Un ERP no debe ser un espejo del catálogo del distribuidor. Debe contener **tus** productos (lo que vendes/cotizas/compras/almacenas) y **consultar** el resto bajo demanda.

**Recomendación:** migrar a un **modelo híbrido** — Odoo guarda solo los productos *en uso* (con datos enriquecidos y refresco diferenciado de precio/stock); el resto del catálogo se **consulta en vivo vía API** al cotizar, y se "promueve" a producto real solo cuando se va a transaccionar. Además, **rediseñar la capa de integración** para soportar varios distribuidores (CVA, CT, Ingram…) sobre el modelo nativo de Odoo (`product.supplierinfo`) en vez de columnas `syscom_*` acopladas.

**Impacto esperado:** base de datos de ~8 GB de imágenes → cientos de MB; cron de 63 min con timeout → segundos; precios/stock **realmente** al día (hoy no lo están porque el cron no acaba); y una base lista para multi-distribuidor.

---

## 1. Diagnóstico del estado actual

### 1.1 Cómo está construida hoy la integración
- **Módulo único `sentinela_syscom`** (Odoo 18 Community), acoplado directamente al modelo `product.template` con **17 campos `syscom_*`** (id, marca, modelo, descripción, stock, 3 precios USD, peso, link, descripción/clave-unidad SAT, características HTML, URL de ficha, descontinuado + fecha, última actualización).
- **Autenticación:** OAuth client_credentials con **token cacheado ~365 días** (`token_cache`/`token_expiry`). Bien resuelto.
- **Conexión:** `requests.Session` con pooling + `Retry` (backoff, respeta `Retry-After` en 429/5xx) + **rate limiter** propio bajo `max_requests_per_min` (280; límite real API ~300). Técnicamente sólido.
- **Cron nocturno único** `ir_cron_syscom_sync` (`_cron_update_syscom_products`, 1×día 03:00), rediseñado en v18.0.1.7.0 en 3 fases:
  - **Fase 1 — barrido por listado:** por cada marca/categoría de Ajustes pagina `/productos?marca=&pagina=` (60/pág). El listado ya trae precio+stock+SAT, así que **actualiza los existentes sin llamada de detalle** y junta los nuevos; los nuevos se enriquecen con `/productos/{id}` **en paralelo** (ThreadPool 8) y se crean.
  - **Fase 2 — refresh de "no barridos":** productos ligados que el barrido no tocó → detalle 1×1; **detecta descontinuados** (404 / flag).
  - **Fase 3 — limpieza de descontinuados:** borra los sin movimiento, archiva los con movimiento (si `autodelete_discontinued`).
  - Commits por lote para sobrevivir cortes; reporte a Telegram.
- **Alta bajo demanda (ya existe):** `syscom.import.wizard` busca en la API en vivo (`/productos?busqueda=`), trae el detalle del SKU elegido y lo crea con SAT/precio/ficha. **Esta pieza ya implementa el patrón correcto.**
- **Enriquecimiento (`_syscom_extract_enrichment`):** de la ficha de detalle saca descripción SAT, clave de unidad SAT, características (→HTML) y **la primera** "ficha técnica" (`recursos[]`). La imagen de portada se baja **solo al crear**.

### 1.2 Métricas reales (PROD, 28-jun-2026)
| Indicador | Valor | Lectura |
|---|---|---|
| Productos totales | **46,910** | — |
| Ligados a Syscom (`syscom_id`) | **46,843** | ~todo el catálogo |
| Con movimiento real | **36** (0.08%) | lo que de verdad usamos |
| Con stock | **0** | no almacenamos inventario Syscom |
| Marcadas vendibles/comprables | **46,837** | ruido total en ventas y compras |
| Categorías | **980** (950 de Syscom) | árbol completo espejado |
| **Imágenes (filestore)** | **165,515 adjuntos · ~7.6 GB** | costo oculto enorme |
| Marcas configuradas para importar | **338** | = "tráete casi todo" |
| Tamaño tabla `product_template` | 173 MB | — |
| Importación masiva | Ene 1.7K · Feb 9.6K · **Jun 35.4K** | crecimiento reciente sin control |

### 1.3 La corrida de anoche
El cron arrancó 03:00, y **a los ~63 min Odoo lo mató por timeout** (`Job ... timed out`), atorado en `_syscom_fetch_details` (detalle de nuevos). **No completó.** Conclusión empírica: el diseño actual **no es capaz de mantener el volumen que él mismo importa.**

---

## 2. Problemas detectados

1. **Sobre-espejado del catálogo (causa raíz).** 46.8K productos para vender 36. La "lista de 338 marcas" es, en la práctica, "importa casi todo Syscom". El ERP dejó de modelar *nuestro* negocio y pasó a ser una copia desactualizada del catálogo del proveedor.
2. **El cron no termina (timeout).** Recorrer decenas de miles de productos cada noche no escala. Y como no termina, **los precios/stock NO quedan al día** — se obtiene lo contrario del objetivo.
3. **Costo de almacenamiento desproporcionado.** ~7.6 GB de imágenes (y sus 5 variantes por producto) para productos 99.9% sin uso. Esto infla **respaldos**, **filestore** y tiempos de restore.
4. **Ruido operativo.** 46,837 productos `sale_ok`/`purchase_ok` ensucian toda búsqueda en Ventas, Compras y POS. 980 categorías vuelven inmanejable el árbol.
5. **Datos "frescos" que no lo son.** Stock = 0 en todo y precios que el cron no alcanza a refrescar ⇒ el catálogo espejado es **poco confiable** justo donde importa (cotizar con precio/disponibilidad real).
6. **Arquitectura acoplada a un solo proveedor.** Los campos `syscom_*` viven directamente en `product.template` y la lógica en `product.py`. Para CVA/CT/Ingram habría que **duplicar campos y crons** por proveedor, y un mismo producto ofrecido por 3 distribuidores **no se puede modelar**.
7. **API infrautilizada pese al volumen.** Irónicamente, aunque guardamos *muchos* productos, **no aprovechamos** datos valiosos de la API: **accesorios**, **productos relacionados**, **múltiples documentos/recursos** (solo se guarda 1 ficha), galería de imágenes, jerarquía completa de categoría por producto. Se guarda *cantidad*, no *riqueza*.

---

## 3. Riesgos de la arquitectura actual

| Riesgo | Severidad | Detalle |
|---|---|---|
| **Precios/stock desactualizados** al cotizar | 🔴 Alto | El cron no termina; se cotiza con datos viejos → margen mal calculado, vender lo descontinuado. |
| **Respaldos pesados / restore lento** | 🟠 Medio-alto | 7.6 GB de imágenes inútiles inflan el backup diario y el tiempo de recuperación ante desastre. |
| **Degradación de rendimiento** | 🟠 Medio | Búsquedas de producto, reportes e índices sobre 47K registros con 5 imágenes c/u. |
| **Errores fiscales** | 🟠 Medio | Productos sin clave SAT correcta entre 47K → CFDI rechazado (ya pasó: `01010101` vs 8% frontera). Con menos productos, controlable. |
| **Deuda técnica multi-proveedor** | 🟠 Medio | Acoplamiento a Syscom encarece añadir distribuidores; refactor caro si se posterga. |
| **Operación frágil** | 🟡 Bajo-medio | El cron grande choca con el framework si se corre a mano (lock `ir_cron`, idle-in-tx) — ya documentado como trampa. |

---

## 4. Alternativas de arquitectura

### Opción A — Catálogo completo en Odoo (lo actual, "mirror")
Mantener todo Syscom espejado en `product.template`.
- **A favor:** todo "buscable" dentro de Odoo sin salir; cero dependencia de la API al cotizar.
- **En contra:** no escala (timeout), 7.6 GB de imágenes, datos desactualizados, ruido, no multi-proveedor. **Es el modelo que ya falló.**
- *Para que funcionara* habría que sincronizar **por tandas/delta** (no todo cada noche) y mover imágenes fuera de la DB — parches que no resuelven el problema de fondo (modelar lo que no usamos).

### Opción B — Catálogo 100% bajo demanda (sin almacenar)
Odoo guarda **solo** lo que se transacciona; **todo lo demás se consulta en vivo** vía API (el wizard ya lo hace).
- **A favor:** base mínima y limpia, siempre fresco, cron trivial, simple.
- **En contra:** no puedes "navegar/buscar" el catálogo dentro de Odoo sin pedirle a la API cada vez; depende de la disponibilidad de la API para descubrir productos; sin vista offline del catálogo.

### Opción C — Modelo híbrido ⭐ (recomendado)
Odoo guarda **los productos en uso** (datos completos y refresco diferenciado). El catálogo **no transaccionado se consulta bajo demanda** vía API y se **promueve** a producto real solo al transaccionar. Opcionalmente, un **índice ligero de catálogo** (solo metadatos: id, nombre, marca, categoría, precio, stock, miniatura-URL — **sin binarios**) para buscar/navegar dentro de Odoo sin inflar `product.template`.
- **A favor:** combina lo mejor de A y B — base esbelta y rápida, frescura real, catálogo navegable (vía índice o búsqueda en vivo), y encaja con multi-proveedor.
- **En contra:** un poco más de diseño (capa de búsqueda + promoción). Es complejidad *justificada* y estándar en ERPs serios.

---

## 5. Recomendación técnica

**Adoptar la Opción C (híbrido) sobre el modelo nativo de proveedores de Odoo, con una capa de conector multi-distribuidor.**

### 5.1 Principios
1. **`product.template` = nuestros productos**, no el catálogo del proveedor. Solo lo que vendemos/cotizamos/compramos/almacenamos.
2. **El precio/código/stock del distribuidor van en `product.supplierinfo`** (modelo nativo "Proveedores" de Odoo, multi-vendor por producto, con lista de precios y plazos). Esto resuelve de raíz el multi-distribuidor: un producto puede tener a Syscom, CVA y CT como proveedores con su precio/código cada uno; Odoo ya elige el mejor.
3. **El catálogo externo es una *fuente*, no un *almacén*.** Se consulta bajo demanda; se promueve al transaccionar.
4. **Refresco diferenciado** por tipo de dato (no todo a la misma frecuencia).
5. **Conector por distribuidor** detrás de una interfaz común → añadir CVA/CT/Ingram = implementar el conector, no tocar el núcleo.

### 5.2 Diseño objetivo
```
            ┌─────────────────────────────────────────────┐
            │  product.template  (SOLO productos en uso)   │  ← datos ricos: imágenes,
            │  + product.supplierinfo (Syscom, CVA, CT...) │    ficha, accesorios, SAT
            └───────────────▲─────────────────────────────┘
   promueve al transaccionar │  refresco precio/stock (solo lo nuestro)
            ┌───────────────┴─────────────────────────────┐
            │   Capa de conector de distribuidores         │
            │   distributor.connector (interfaz común):    │
            │   search() · get_product(ref) · price_stock()│
            │   ├─ SyscomConnector   (hoy)                 │
            │   ├─ CVAConnector      (futuro)              │
            │   └─ CTConnector, Ingram, ...               │
            └───────────────▲─────────────────────────────┘
                            │  API en vivo / índice ligero opcional
            ┌───────────────┴─────────────────────────────┐
            │  syscom.catalog.item (OPCIONAL, índice ligero│
            │  para buscar/navegar dentro de Odoo: id,     │
            │  nombre, marca, categoría, precio, stock,    │
            │  URL-miniatura — SIN binarios, SIN 5 vars)   │
            └─────────────────────────────────────────────┘
```

### 5.3 Estrategia de actualización (frecuencias diferenciadas)
| Dato | Frecuencia | Mecanismo | Por qué |
|---|---|---|---|
| **Tipo de cambio USD** | 1×/día | cron ligero | base de todos los precios MXN. |
| **Precio (lista USD)** de productos en uso | 1×/día (madrugada) | refresco solo de los nuestros (cientos) | el precio cambia poco; barato y rápido. |
| **Existencias** de productos en uso | varias veces/día (ej. cada 2-4 h) o **en vivo al cotizar/comprar** | API puntual por SKU | el stock es volátil; lo crítico es tenerlo fresco *en el momento de la cotización/OC*, no de madrugada. |
| **Existencia/precio de un producto NO almacenado** | en vivo (on-demand) | conector `price_stock(ref)` | no se guarda; se consulta al necesitarlo. |
| **Enriquecimiento** (imágenes, ficha, accesorios, relacionados, documentos, SAT) | al **promover** + refresco esporádico (semanal/mensual) | detalle `/productos/{id}` | cambia muy poco; no requiere tocarse a diario. |
| **Catálogo nuevo / descontinuados** | semanal o delta | índice ligero / barrido acotado a marcas core | descubrir novedades sin recorrer todo a diario. |

### 5.4 Imágenes y documentación técnica
- **No almacenar binarios masivamente.** Para productos en uso: guardar **la imagen principal** (y opcional galería) y, para el resto, **referenciar la URL del CDN de Syscom** (carga diferida / miniatura). Las fichas técnicas y documentos: **guardar la URL**, no el PDF (Syscom los hospeda).
- Esto sólo ya **recupera ~7.6 GB** y aligera respaldos.
- Considerar mover el **filestore fuera de la DB** (ya lo está en Odoo 18 por defecto) y, a futuro, a almacenamiento de objetos (S3/MinIO) si crece.

### 5.5 Eliminar vs archivar vs marcar obsoleto (política clara)
| Situación del producto | Acción | Razón |
|---|---|---|
| **En uso** (movimiento/stock) | **Conservar** siempre | integridad operativa/contable. |
| En uso **y** descontinuado por Syscom | **Archivar** (`active=False`) + marcar `syscom_discontinued` | preserva historia contable, sale de las búsquedas. |
| **Sin uso** y nunca transaccionado | **Eliminar** | no hay historia que proteger; se re-importa al instante si se necesita. |
| Descontinuado **sin uso** | **Eliminar** | igual que arriba. |
> "Descontinuado" (estado del proveedor) ≠ "no lo manejamos" (no debería estar en `product.template`). La limpieza inicial es un caso particular de esto: ~46,800 sin uso → eliminar.

### 5.6 Aprovechar TODA la API (lo que hoy NO usamos)
Para los productos **en uso/promovidos**, capturar lo que la API ofrece y hoy se ignora:
- **Accesorios** y **productos relacionados** → mapear a `accessory_product_ids` / `alternative_product_ids` nativos de Odoo (venta cruzada, kits).
- **Todos los documentos/recursos** (no solo la primera "ficha") → lista de adjuntos por URL.
- **Galería de imágenes** (no solo portada).
- **Atributos/características** estructurados (ya se hace parcialmente, en HTML; valorar atributos reales).
- **Jerarquía de categoría** por producto (ya se mapea).
- Clave SAT y clave de unidad (ya, pero asegurarlo siempre, no opcional).

### 5.7 Ventajas y desventajas de la recomendación
**Ventajas**
- Base esbelta: búsquedas, reportes y respaldos rápidos.
- Precio/stock **realmente** frescos (poco volumen → siempre completa; stock en vivo al cotizar).
- Catálogo completo accesible (búsqueda en vivo y/o índice ligero) **sin** inflar el ERP.
- Datos ricos (accesorios, fichas, imágenes) donde aportan valor (lo que vendes).
- **Multi-distribuidor nativo** vía `product.supplierinfo` + conectores → CVA/CT/Ingram sin reescribir el núcleo.
- Alineado a buenas prácticas Odoo (no se inventan estructuras paralelas).

**Desventajas / costos**
- Requiere **refactor** (no solo limpiar): mover datos de proveedor a `supplierinfo`, crear la capa de conector, opcional índice ligero.
- La búsqueda del catálogo no-almacenado **depende de la API** (mitigado con índice ligero y caché).
- Esfuerzo de migración y pruebas (por eso va por fases).

---

## 6. Plan de implementación por fases

> Cada fase es entregable e independiente; **STAGING primero**, validación, luego PROD. Reversible donde aplica.

**Fase 0 — Resguardo y línea base (0.5 día)**
- Respaldo completo (DB + filestore). Exportar a CSV los 36 productos en uso y los 67 manuales/servicios (lista blanca).
- Congelar el cron actual (ya configurable desde Ajustes).

**Fase 1 — Limpieza y recuperación de espacio (1 día)**
- Eliminar los productos Syscom **sin movimiento ni stock** (~46,800) y sus imágenes/variantes; podar categorías huérfanas.
- Resultado medible: `product.template` y filestore caen drásticamente (~7.6 GB liberados). Validar que ventas/compras/facturas siguen íntegras (la lista blanca queda intacta).

**Fase 2 — Cron escalable (refresco solo de lo nuestro) (1 día)**
- Reescribir el cron para iterar **únicamente productos en uso** (vía `product.supplierinfo` con proveedor Syscom). Separar en crons independientes: (a) tipo de cambio 1×día, (b) precio 1×día, (c) stock cada 2-4 h (o en vivo).
- Resultado: corre en segundos, sin timeout, completo siempre.

**Fase 3 — Alta y enriquecimiento bajo demanda (1-2 días)**
- Reforzar el wizard de importación como vía oficial de alta; al promover un producto, traer **imágenes, ficha, accesorios, relacionados, documentos, SAT** completos.
- Stock/precio en vivo al agregar a cotización/OC (campo "consultar disponibilidad").

**Fase 4 — Abstracción multi-distribuidor (2-4 días)**
- Introducir `distributor.connector` (interfaz común) y mover Syscom a `SyscomConnector`. Migrar los datos de proveedor de columnas `syscom_*` a `product.supplierinfo` (conservando lo informativo en campos propios mínimos).
- Deja listo el terreno para CVA/CT/Ingram (cada uno = un conector).

**Fase 5 — (Opcional) Índice ligero de catálogo + búsqueda unificada (2-3 días)**
- `distributor.catalog.item` (metadatos, sin binarios) alimentado por delta/semanal, para navegar/buscar el catálogo completo dentro de Odoo y "promover" con un clic.

**Fase 6 — Multi-distribuidor real (cuando se sume el 2.º proveedor)**
- Implementar el segundo conector (p. ej. CVA), comparar precios/stock entre distribuidores en `supplierinfo`, y dejar que Odoo elija el mejor proveedor por OC.

---

## 7. Impacto esperado

| Dimensión | Hoy | Con la propuesta |
|---|---|---|
| **Rendimiento** | 47K productos, búsquedas lentas, cron 63 min con **timeout** | cientos de productos, búsquedas ágiles, cron en **segundos** |
| **Frescura de datos** | precios/stock **desactualizados** (cron no acaba) | precio diario completo + **stock en vivo** al cotizar |
| **Almacenamiento/respaldo** | **~7.6 GB** imágenes + 173 MB tabla | de cientos de MB; respaldos y restore mucho más rápidos |
| **Calidad de catálogo** | mucho volumen, poca riqueza, ruido | menos productos, **datos ricos** (accesorios/fichas/imágenes) donde importan |
| **Mantenimiento** | frágil, acoplado a Syscom, trampas de cron | crons pequeños y separados; política clara de obsoletos |
| **Escalabilidad multi-proveedor** | **no soportado** (campos `syscom_*`) | nativo vía `supplierinfo` + conectores |
| **Riesgo fiscal (SAT)** | claves dudosas entre 47K | controlable en un catálogo acotado y enriquecido |

---

## Apéndice — Cómo se obtuvieron estas cifras
- Conteos y pesos: consultas SQL directas a `Sentinela_V18` (28-jun-2026): `product_template`, `ir_attachment` (res_field de imagen), `sale_order_line`/`purchase_order_line`/`account_move_line`/`stock_move`/`stock_quant` para "movimiento", `ir_config_parameter` (marcas/categorías), `pg_total_relation_size`.
- Arquitectura del código: `sentinela_syscom/models/product.py` (cron 3 fases, sesión/retry, rate limiter, enriquecimiento), `wizard/syscom_import_wizard.py` (alta en vivo), `models/res_config_settings.py`, `CLAUDE.md` del módulo.
- Corrida del cron: logs del contenedor `odoo18-migration-web-1` (28-jun 09:00–10:03 UTC, `timed out`).

> **Nada de esto se ha ejecutado aún.** Es la base técnica para decidir. Mi recomendación es aprobar la **Opción C** y arrancar por **Fase 0-1-2** (limpieza + cron escalable), que resuelven el dolor inmediato y liberan 7.6 GB, dejando 3-6 para cuando se quiera el enriquecimiento profundo y el multi-distribuidor.

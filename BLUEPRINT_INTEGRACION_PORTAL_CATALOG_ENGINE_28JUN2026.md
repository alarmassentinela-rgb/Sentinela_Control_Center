# Blueprint de Integración — Portal de Clientes ↔ Catalog Engine v1.0 LTS

**Fecha:** 28-jun-2026 · **Estado:** diseño para validación (NO se escribe código aún) · Alea Platform.
**Catalog Engine v1.0 LTS congelado.** El Portal será su **primer consumidor oficial**.

---

## Objetivo
Integrar el Portal de Clientes con el Catalog Engine **sin acoplar el Portal a Odoo ni a Syscom**.
**Toda consulta de catálogo se hace por la Catalog Public Interface v1** (`/catalog/api/v1`).
El Portal nunca conoce el ORM de Odoo ni la API de Syscom: solo contratos HTTP estables.

## Topología (quién habla con quién)
```
  Cliente (web/app) ──► Portal SPA (Next.js) ──► Gateway BFF (FastAPI, api.sentinela.mx)
                                                   │
                                ┌──────────────────┴───────────────────┐
                                ▼                                       ▼
                 Catalog Public Interface v1              ERP API (sentinela_api / Odoo)
                 /catalog/api/v1  (API key de servicio)   datos del cliente (auth por cliente)
                 búsqueda · stock · specs · imágenes       contratos · membresías · facturas ·
                 · documentos · promote                     tickets · OS · dispositivos · eventos
```
El **Gateway BFF** es el único punto que habla con ambas plataformas y compone la respuesta para la SPA/app.

---

## 1. Funcionalidades del Portal que consumen el Catalog Engine
Vía `/catalog/api/v1`:
| Función del Portal | Endpoint Catalog | Nota |
|---|---|---|
| Búsqueda de productos | `GET /products` (q, filtros, orden, paginación) | índice 2-fases; rápido a 1M |
| Ficha de producto | `GET /products/{ref}` | refresca on-demand si vencido |
| Disponibilidad (stock) | `GET /products/{ref}` → `stock` + `freshness` | indicativo; autoritativo al cotizar |
| Precio (catálogo) | `GET /products/{ref}` → `price` | ⚠️ ver §4 (NUNCA exponer `cost` al cliente) |
| Fichas técnicas / documentos | `product.documents` (URL) | solo URL (CDN del proveedor) |
| Imágenes | `images`/`thumb_url` (URL) | sin binarios |
| Productos relacionados | (ver nota) | **la API de distribuidor NO los da**; vienen del producto maestro (ERP: accessory/alternative) tras promoverse, o manual |

## 2. Información que el Portal sigue obteniendo del ERP (no del Catalog Engine)
Vía la **ERP API (`sentinela_api`)**, autenticada **por cliente**:
contratos · **membresías** · facturas/CFDI · tickets/mesa de ayuda · órdenes de servicio (FSM) · dispositivos instalados · eventos/alarmas (monitoreo).
> Regla: el **Catalog Engine** responde "¿qué productos existen y cómo son?"; el **ERP** responde "¿qué tiene/contrató ESTE cliente?".

## 3. APIs: las que ya existen vs. las que faltan
**Ya disponibles (Catalog v1):** `GET /products`, `GET /products/{ref}`, `POST /products/{ref}/promote`, `GET /health`, `GET /metrics`, OpenAPI/Swagger/JSON-Schema.
**Ya disponibles (ERP):** `sentinela_api` (Mis Servicios, Facturación) del Portal COC.
**Por desarrollar después (no en este blueprint):**
- Catalog: endpoint de **precio público al cliente** (lista sin `cost`) o un parámetro `view=public`; endpoint de **relacionados/accesorios** del maestro; (futuro) **cotización/carrito**.
- ERP: lo que falte de tickets/OS/dispositivos según el alcance del Portal.
> Cada API nueva pasará por la regla de las 3 preguntas (Master Plan) y respetará el versionado (`/v1`→`/v2`).

## 4. Permisos: qué necesita un cliente para consumir el catálogo
- **El catálogo NO es por-cliente.** El **Gateway** posee **una API key de servicio** del Catalog Engine (scope `read`) y consulta en nombre de los clientes autenticados en el Portal.
- **La autenticación del cliente final** ocurre en el Portal/ERP (su sesión), no en la Catalog API.
- ⚠️ **Seguridad de datos:** el DTO de catálogo incluye `price.cost` (costo del distribuidor, **interno**). El Gateway **debe filtrar `cost`** y nunca enviarlo a la SPA/app. El **precio que ve el cliente** es el **precio de venta del ERP** (lista/contrato/membresía), no el costo del distribuidor. *(Recomendación 1.1: un endpoint/vista pública del Catalog que ya no devuelva `cost`.)*
- `promote` (scope `promote`) lo usa el **Gateway/ERP**, no el cliente.

## 5. Caché del Portal (minimizar llamadas)
- El **Gateway BFF cachea** las respuestas del Catalog Engine con **TTL alineado a la frescura** del motor: stock corto (~min), precio medio (~horas), fichas/imágenes largo (~días).
- El Catalog ya entrega `freshness.expires_at` por canal → el Gateway lo respeta como pista de TTL.
- Búsquedas populares y fichas se cachean; el stock crítico se confirma en vivo al momento de cotizar.
- Capa de caché reemplazable (memoria→Redis) en el Gateway, igual que en el motor.

## 6. Independencia entre Portal · Catalog Engine · Membresías · ERP
- **Portal** depende de **contratos HTTP** (Catalog v1 + ERP API). No conoce Odoo ni Syscom.
- **Catalog Engine** y **Membresías** son independientes; comparten solo `product.template` (Membresías NO se consume por la Catalog API; sus planes son productos propios excluidos del catálogo).
- **ERP** es el sistema de registro del cliente; el Catalog es la fuente del catálogo. Nadie hace `depends` cruzado de código; todo es por API.
- Direcciones permitidas: `Portal → Catalog v1`, `Portal → ERP API`. Prohibido: `Portal → Odoo ORM`, `Catalog ↔ Membresías` (código).

## 7. Preparación para la App Móvil (mismas APIs)
- La App consume **exactamente** `Catalog Public Interface v1` + `ERP API` (los mismos contratos que la SPA).
- El Gateway BFF sirve a web y móvil por igual; nada específico de Odoo se filtra al cliente.
- API-First + versionado + OpenAPI → la App se construye **leyendo la misma documentación**, sin nuevos contratos.

---

## Hallazgos clave (a validar antes de codificar)
1. **`cost` es interno** → el Gateway debe filtrarlo; el precio al cliente viene del ERP. *(posible endpoint público de catálogo en 1.1).*
2. **Relacionados/accesorios** no los da la API del distribuidor → vienen del maestro (ERP) o se capturan manualmente.
3. **Precio/stock al cotizar** debe confirmarse en vivo (no solo caché) para no vender con datos viejos.
4. El Portal mezcla dos fuentes (Catalog + ERP) → el **Gateway** es quien compone; mantenerlo delgado y sin lógica de negocio duplicada.

## Entregable
Este **Blueprint de Integración Portal ↔ Catalog Engine** (sin código). Próximo paso (tras tu visto bueno): plan de implementación por fases en STAGING (gateway→Catalog v1, caché, filtrado de `cost`, composición con ERP API), con la misma disciplina de entregables+pruebas+reporte.

# Blueprint v1.1 — Requisitos transversales (proyecto estratégico Alea Systems)

**Fecha:** 28 de junio de 2026 · **Adenda de** `BLUEPRINT_MOTOR_CATALOGO_28JUN2026.md`.
Incorpora 8 requisitos no funcionales/transversales que aplican a **todo** el Motor de Catálogo y **se construyen desde D1** (no se posponen). Autorización vigente: **solo D0–D3 en STAGING**, sin tocar producción ni migraciones destructivas; reporte y aprobación por entregable.

---

## R1. API First — Odoo es un consumidor más
- **Arquitectura en 3 capas** dentro del motor: **Controladores (transporte)** → **Servicios (lógica de negocio, agnósticos de transporte)** → **Modelos/ORM**. La lógica vive en **servicios**, nunca en vistas ni controladores.
- **API interna REST/JSON** versionada: `/catalog/api/v1/...` (Odoo `http.Controller`, `type='json'`), con **autenticación por API key / OAuth2 client-credentials** y *scopes*. Endpoints: `search`, `product/{ref}`, `price_stock`, `promote`, `rules/quote`, `metrics`.
- Consumidores: **Odoo (UI), Portal COC, tienda en línea, apps móviles, sistemas de IA, otros sistemas de Alea**. Todos llaman a los **mismos servicios**.
- **Contrato estable** documentado (OpenAPI). El `NormalizedProduct` es el DTO público.
- *Aterriza en:* **D1** (capa de servicios + esqueleto de API y auth), **D3** (endpoints de búsqueda/índice), **D4** (promote).

## R2. Observabilidad — métricas desde la primera versión
- **Instrumentación en el `connector_base`**: cada llamada pasa por un *wrapper* que mide y registra.
- **Modelos:** `catalog.run` (una corrida: cron/manual/api — inicio, fin, duración, resultado) y `catalog.metric` (serie por backend/operación).
- **Métricas por conector/corrida:** tiempo de respuesta API, nº de consultas, errores (por tipo/código), productos sincronizados / promovidos / descartados, **consumo de cuota** (vs rate-limit), **duración de cron**, **uso de caché (hit/miss ratio)**.
- **Panel** (vistas Odoo + gráficas) y **endpoint `/metrics`** (formato Prometheus) para integrar Grafana/alertas a futuro.
- *Aterriza en:* **D1** (instrumentación + modelos), **D3** (panel + endpoint).

## R3. Configuración por distribuidor — sin tocar código
Todo en **`distributor.backend`** (editable en Ajustes), por distribuidor e independiente:
- Prioridades (política de `sync_tier`), **horarios** de sincronización (por tipo de dato), **TTL de caché** (precio/stock/enriquecimiento), **límite de llamadas**, **política de imágenes** (URL/local), **política de documentos** (URL/local), **estrategia de actualización** (listado/detalle/delta).
- El conector y el motor **leen** la config; el código no cambia al ajustar parámetros.
- *Aterriza en:* **D1** (modelo + campos + UI), usado desde **D3/D5**.

## R4. Reglas de negocio — independientes del conector
- **Motor de reglas** en el núcleo (`catalog.rule`, `catalog.pricing.rule`): **margen mínimo**, **margen por marca**, **margen por categoría**, **proveedor preferido / alternativo**, **sustitución automática** cuando el preferido no tiene stock, **exclusión** de productos/marcas.
- Se evalúan en el **servicio de precios/abasto** (no en el conector). Se apoyan en `pricelist`/`supplierinfo` nativos donde aplique.
- Expuestas por API (`rules/quote`) para que cualquier consumidor obtenga el precio/abasto ya "con reglas".
- *Aterriza en:* **D6+** (tras tener precios/stock por distribuidor); el **modelo** se reserva desde D1 para no romper migraciones.

## R5. Auditoría — toda sincronización auditable
- **`catalog.audit.log`** (núcleo): qué cambió, cuándo, **qué proveedor lo reportó**, **qué usuario** promovió, **qué proceso** (cron/api/wizard/usuario) modificó un precio, valor anterior/nuevo.
- Complementa `distributor.price.history` (precios) + tracking nativo `mail.thread` en los modelos clave.
- Inmutable/append-only; consultable por producto, por backend y por corrida (`catalog.run`).
- *Aterriza en:* **D1** (modelo + hooks base), poblado por cada operación desde D2/D3.

## R6. Pruebas automatizadas — gate de calidad
- Cada módulo trae `tests/` (Odoo `TransactionCase`).
- **Conectores:** unitarias (`normalize()` con *fixtures* de payload real) + integración (API **mockeada** / *cassettes* grabadas; sin pegarle a la API real en CI).
- **Núcleo:** índice, caché/TTL, prioridades, promoción, reglas.
- **Regla:** **no se aprueba** un conector/entregable si las pruebas no pasan. Cobertura reportada en cada entrega.
- *Aterriza en:* **todos** los entregables (parte del criterio de aceptación).

## R7. Documentación — desde el inicio
- Cada módulo: `README` + `CLAUDE.md` (cómo es el código) + docstrings.
- **Guía "Cómo agregar un distribuidor"** (paso a paso, con `distributor_syscom` como plantilla de referencia).
- Contrato de API (OpenAPI) y diccionario de datos del `NormalizedProduct`.
- Objetivo: cualquier dev de Alea integra un distribuidor **sin** depender del equipo original.
- *Aterriza en:* **todos** los entregables.

## R8. Cadencia de desarrollo y reporte
- **Solo D0–D3 en STAGING.** Al cerrar **cada** entregable entrego: **(1) resumen técnico, (2) cambios realizados, (3) evidencia de pruebas, (4) riesgos encontrados, (5) métricas, (6) recomendaciones para la siguiente fase.**
- **No avanzo** al siguiente entregable sin tu aprobación. Sin cambios en producción ni migraciones destructivas.

---

## Impacto en la estructura de módulos (actualiza §1 del Blueprint)
- `distributor_connector_base`: + **instrumentación/observabilidad** (wrapper de métricas), + **`distributor.backend`** ampliado (config R3), + utilidades de auditoría.
- `product_catalog_engine`: + **capa de servicios** (R1), + **API interna `/catalog/api/v1`** (R1), + **`catalog.run`/`catalog.metric`/`catalog.audit.log`** + **panel** (R2/R5), + **motor de reglas** `catalog.rule` (R4), + endpoint `/metrics`.
- Cada `distributor_xxx`: + **tests** (R6) + **docs** (R7) obligatorios.

## Criterios de aceptación adicionales (se suman a §8 del Blueprint)
- **D1** aprueba si además: instrumentación de métricas activa, modelos `catalog.run/metric/audit.log` creados, `distributor.backend` con la config de R3, esqueleto de capa de servicios + auth de API, **tests verdes**, **README+CLAUDE.md**.
- **D2** aprueba si además: tests de `normalize()` con *fixtures* reales verdes; cada llamada deja métrica + auditoría; documentado.
- **D3** aprueba si además: panel de métricas visible; endpoints `/catalog/api/v1/search|product` funcionando vía API (no solo UI); config por distribuidor efectiva; tests verdes.

> Estos requisitos **no agregan fases nuevas**; refuerzan D1–D3 (y reservan modelos para D4+). El arranque sigue siendo **D0 → D1 → D2 → D3**, en STAGING, con reporte y aprobación por entregable.

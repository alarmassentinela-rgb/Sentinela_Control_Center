# D3d — Scheduler Inteligente del Motor de Catálogo

**Fecha:** 28-jun-2026 · Módulo `product_catalog_engine` + eventos en `distributor_connector_base` · **Solo STAGING.**
**Criterio de aceptación (#7):** el Motor mantiene la frescura del catálogo **automáticamente y sin recorridos completos**. ✅ Demostrado.

---

## 1. Freshness (metadatos de vigencia)
Cada ítem (`distributor.catalog.item`) lleva, **por canal**: `<canal>_synced_at`, `<canal>_expires_at` (canales: price/stock/enrichment), `sync_source`, y un `freshness_status` (never/fresh/expired) calculado. Así se sabe **qué tan actual** es cada dato y cuándo expira.

## 2. Políticas de sincronización (TTL por tipo de dato)
Modelo configurable `catalog.sync.policy` (por distribuidor o global), defaults sembrados:
| Tipo | TTL |
|---|---|
| Precio | 24 h (1440 min) |
| Existencia | 30 min |
| Enriquecimiento (imágenes/docs/garantía/descripción) | 30 d |
> Imágenes/docs (30 d) y garantía/descripción (90 d) que pediste pertenecen al canal **enrichment** (una sola llamada de detalle los trae juntos). El modelo admite más tipos sin código si se requiere granularidad fina. **No hay un único cron para todo.**

## 3. Prioridades (tiers) — el scheduler decide qué va primero
`_cron_recompute_tiers` recalcula `sync_tier` por uso real:
- **T0** Cotizaciones abiertas · **T1** Vendidos (90 d) · **T2** Favoritos · **T3** Consultados frecuentemente (`hit_count`) · **T4** Catálogo frío (default).
Los crones de refresco ordenan por `sync_tier` → lo importante se refresca primero. (Opera sobre **nuestro índice** acotado, no sobre el catálogo del distribuidor.)

## 4. Crones (uno por tipo de dato)
| Cron | Cadencia | Acción |
|---|---|---|
| Refrescar existencias | 30 min | refresca SOLO stock vencido, por tier, en lote |
| Refrescar precios | 1 h | precio vencido, por tier |
| Refrescar enriquecimiento | 6 h | enriquecimiento vencido, por tier |
| Recalcular prioridades | 1 día | recomputa tiers por uso |
| Detectar calidad | 1 h | vencidos/sin-sync/backlog + evento `CatalogExpired` |
Cada refresco: `WHERE <canal>_expires_at <= now ORDER BY sync_tier LIMIT batch` → **nunca recorre todo**, y cada corrida se registra en `catalog.run` (observabilidad).

## 5. Eventos (concepto #4)
Se emiten a `catalog.event` (+ bus): **PriceChanged**, **StockChanged**, **ProductRefreshed**, **ProductExpired**, **CatalogExpired**, **DistributorUnavailable**, **PromotionRequested**. Base para automatización/IA/notificaciones.

## 6. Calidad (concepto #5)
`_cron_detect_quality` detecta: productos **sin sincronizar**, **datos expirados**, **backlog**; los fallos de refresco emiten `DistributorUnavailable` (APIs caídas). Cuellos de botella/retrasos visibles en el dashboard (corridas, errores, backlog).

## 7. Dashboard (concepto #6)
`catalog.dashboard` (menú **Motor de Catálogo → Estado del Motor**): indexados, promovidos, vigentes, **expirados (backlog)**, sin sincronizar, **por tier**, tiempo prom. de sync, errores 24 h, eventos 24 h, entradas de caché y **desglose por distribuidor**.

## 8. Benchmark (criterio de aceptación #7) — STAGING
| Escenario | Resultado |
|---|---|
| 50,000 ítems (49,500 vigentes + 500 vencidos) | — |
| `_cron_refresh_stock` (lote 200) | **tocó solo 200, por tier, en 0.48 s** |
| Vigentes intactos | **49,500 (no se recorrieron)** |
**Conclusión:** mantiene la frescura procesando **solo lo vencido y prioritario**, en lotes — **sin full scans**. Escala a catálogos grandes. Datos de prueba eliminados.

## 9. Pruebas
**25 tests, 0 failed, 0 errors** (D3a 10 + D3b 8 + **D3d 7**): TTL de políticas, ciclo de frescura/expiración, refresco que actualiza+emite eventos, **cron refresca solo lo vencido (no toca lo vigente)**, recompute de tiers, hits, detección de calidad.

## 10. Recomendaciones para D3c (API REST)
- La API ya consumirá un catálogo **gobernado por frescura**: en `GET product` devolver `freshness_status`/`expires_at`; si un dato está vencido, **refrescar on-demand** (o servir de caché con aviso de antigüedad) antes de responder.
- `register_hit()` al consultar por API → alimenta el Tier 3.
- Exponer el dashboard/estado por endpoint para monitoreo externo.
- Registrar la latencia por distribuidor (de `connector.metrics_summary()`) en `catalog.metric` desde la API para completar el panel.

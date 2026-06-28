"""Bus de eventos en proceso del Motor de Catálogo.

Los emisores publican; los suscriptores se registran (extensibilidad sin tocar al
emisor). La capa Odoo persiste los eventos en `catalog.event` y opcionalmente los
reenvía a bus.bus / automatizaciones / IA.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

_logger = logging.getLogger(__name__)

# --- Catálogo de eventos (constante -> nombre PascalCase) ---
EVT_PRODUCT_DISCOVERED = "ProductDiscovered"
EVT_PRODUCT_PROMOTED = "ProductPromoted"
EVT_PROMOTION_REQUESTED = "PromotionRequested"
EVT_PRICE_UPDATED = "PriceUpdated"
EVT_STOCK_UPDATED = "StockUpdated"
EVT_CATALOG_SYNCED = "CatalogSynced"
EVT_DISTRIBUTOR_UNAVAILABLE = "DistributorUnavailable"
EVT_CACHE_HIT = "CacheHit"
EVT_CACHE_MISS = "CacheMiss"

ALL_EVENTS = frozenset({
    EVT_PRODUCT_DISCOVERED, EVT_PRODUCT_PROMOTED, EVT_PROMOTION_REQUESTED,
    EVT_PRICE_UPDATED, EVT_STOCK_UPDATED, EVT_CATALOG_SYNCED,
    EVT_DISTRIBUTOR_UNAVAILABLE, EVT_CACHE_HIT, EVT_CACHE_MISS,
})


@dataclass
class Event:
    name: str
    backend_key: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"          # cron | api | wizard | user | system
    occurred_at: str = ""           # ISO-8601; lo fija la capa Odoo


class EventBus:
    """Despachador en proceso. Un handler que falla NO tumba a los demás ni al emisor."""

    def __init__(self):
        self._subs: Dict[str, List[Callable[[Event], None]]] = {}

    def subscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        if event_name not in ALL_EVENTS:
            raise ValueError("Evento desconocido: %r" % event_name)
        self._subs.setdefault(event_name, []).append(handler)

    def publish(self, event: Event) -> int:
        if event.name not in ALL_EVENTS:
            raise ValueError("Evento desconocido: %r" % event.name)
        delivered = 0
        for handler in self._subs.get(event.name, []):
            try:
                handler(event)
                delivered += 1
            except Exception:  # noqa: BLE001 - aislamiento de suscriptores
                _logger.exception("Handler de evento %s falló", event.name)
        return delivered


# Bus por defecto del proceso (la capa Odoo puede usar el suyo por registro).
default_bus = EventBus()

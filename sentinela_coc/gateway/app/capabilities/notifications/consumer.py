# -*- coding: utf-8 -*-
"""Notificación de confirmación de pago (S2-012) — consumidor de eventos.

Al `pago.confirmado`, notifica al cliente REUSANDO el canal existente (mail de Odoo /
WhatsApp), vía un puerto `NotificationPort`. NO crea un sistema de mensajería nuevo.
DESACOPLADO del flujo de pagos: solo reacciona al evento (lee del Event Store).

No duplica: reacciona a UN solo tipo de evento (`pago.confirmado`), que se publica una
única vez por pago (webhook idempotente, S2-008). El detalle del pago se toma del
`pago.iniciado` correlacionado (mismo agregado `payment:<id>`).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class NotifyOutcome:
    notified: bool
    partner_id: int | None = None
    reason: str | None = None


class NotificationPort(ABC):
    """Canal de notificación al cliente (reusa el existente; no se reimplementa)."""

    @abstractmethod
    def payment_confirmed(self, partner_id: int, payment_id: str, amount: float, currency: str) -> bool:
        ...


class NotificationsConsumer:
    def __init__(self, channel: NotificationPort, store):
        self._channel = channel
        self._store = store   # CatalogedEventStore

    def on_payment_confirmed(self, payment_id: str) -> NotifyOutcome:
        eventos = self._store.by_aggregate("payment:%s" % payment_id)
        if "pago.confirmado" not in {e.type for e in eventos}:
            return NotifyOutcome(False, reason="no_confirmado")
        ini = next((e for e in eventos if e.type == "pago.iniciado"), None)
        partner_id = ini.payload.get("partner_id") if ini else None
        amount = (ini.payload.get("amount") if ini else None) or 0.0
        currency = (ini.payload.get("currency") if ini else None) or "MXN"
        self._channel.payment_confirmed(partner_id, payment_id, amount, currency)
        return NotifyOutcome(True, partner_id=partner_id)


class FakeNotificationChannel(NotificationPort):
    """Para pruebas: registra los envíos."""

    def __init__(self):
        self.sent: list[tuple] = []

    def payment_confirmed(self, partner_id, payment_id, amount, currency) -> bool:
        self.sent.append((partner_id, payment_id, amount, currency))
        return True


class OdooNotificationChannel(NotificationPort):
    """Implementación real: endpoint interno que REUSA el canal de mail existente de
    Odoo (sin crear mensajería nueva). Validación viva: S2-015."""

    def __init__(self, base_url: str, shared_secret: str):
        self._base = base_url.rstrip("/")
        self._secret = shared_secret

    def payment_confirmed(self, partner_id, payment_id, amount, currency) -> bool:
        import httpx
        payload = {"jsonrpc": "2.0", "method": "call", "params": {
            "partner_id": partner_id, "payment_id": payment_id,
            "amount": amount, "currency": currency}}
        r = httpx.post("%s/coc/internal/notify/payment_confirmed" % self._base, json=payload,
                       headers={"X-COC-Secret": self._secret}, timeout=20)
        r.raise_for_status()
        return bool(((r.json() or {}).get("result") or {}).get("ok"))

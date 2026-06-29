# -*- coding: utf-8 -*-
"""Motor de Pago (S2-005).

Orquesta el cobro a través de la interfaz `PaymentAdapter`. **NUNCA referencia a un
proveedor concreto** (ni Stripe ni otro): cambiar de proveedor = cambiar el adaptador
que se le inyecta. Aquí vive solo la lógica agnóstica del proveedor.

En este sprint expone autorizar/confirmar. La validación contra el Ledger, la
publicación de eventos y la idempotencia/conciliación llegan en S2-007/008/009.
"""
from .port import InvalidPaymentIntent, PaymentAdapter, PaymentIntent, PaymentResult


class PaymentEngine:
    def __init__(self, adapter: PaymentAdapter):
        self._adapter = adapter

    def authorize(self, intent: PaymentIntent) -> PaymentResult:
        """Autoriza una intención de cobro vía el adaptador. Guarda mínima agnóstica:
        el monto debe ser positivo y traer clave de idempotencia."""
        if intent.amount <= 0:
            raise InvalidPaymentIntent("monto no positivo: %s" % intent.amount)
        if not intent.idempotency_key:
            raise InvalidPaymentIntent("falta idempotency_key")
        return self._adapter.authorize(intent)

    def confirm(self, provider_ref: str) -> PaymentResult:
        """Confirma el estado final de un cobro vía el adaptador."""
        return self._adapter.confirm(provider_ref)

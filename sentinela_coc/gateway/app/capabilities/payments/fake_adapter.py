# -*- coding: utf-8 -*-
"""FakePaymentAdapter (S2-005) — adaptador de pago para pruebas (sin proveedor real).

Devuelve un resultado configurable y registra las llamadas. Permite probar el Motor
de forma determinista sin red ni Stripe.
"""
from .port import CONFIRMED, PaymentAdapter, PaymentIntent, PaymentResult


class FakePaymentAdapter(PaymentAdapter):
    def __init__(self, status: str = CONFIRMED, reason: str | None = None,
                 client_action: dict | None = None):
        self._status = status
        self._reason = reason
        self._client_action = client_action
        self.authorized: list[PaymentIntent] = []
        self.confirmed: list[str] = []
        self.refunded: list[tuple[str, float | None]] = []
        self._seq = 0

    def _ref(self) -> str:
        self._seq += 1
        return "fake-pay-%d" % self._seq

    def authorize(self, intent: PaymentIntent) -> PaymentResult:
        self.authorized.append(intent)
        return PaymentResult(status=self._status, provider_ref=self._ref(),
                             reason=self._reason if self._status == "rejected" else None,
                             client_action=self._client_action)

    def confirm(self, provider_ref: str) -> PaymentResult:
        self.confirmed.append(provider_ref)
        return PaymentResult(status=self._status, provider_ref=provider_ref,
                             reason=self._reason if self._status == "rejected" else None)

    def refund(self, provider_ref: str, amount: float | None = None) -> PaymentResult:
        # Stub: el reembolso está fuera de alcance del Sprint 2.
        self.refunded.append((provider_ref, amount))
        return PaymentResult(status="processing", provider_ref=provider_ref)

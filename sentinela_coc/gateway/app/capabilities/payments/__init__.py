# -*- coding: utf-8 -*-
"""Capacidad Pagos (Cobranza) — puerto + Motor (S2-005).

El Motor depende SOLO de `PaymentAdapter`. Stripe será el primer adaptador (S2-006).
"""
from .fake_adapter import FakePaymentAdapter
from .port import (
    CONFIRMED,
    PROCESSING,
    REJECTED,
    STATUSES,
    InvalidPaymentIntent,
    PaymentAdapter,
    PaymentIntent,
    PaymentResult,
)
from .service import PaymentEngine

__all__ = [
    "PaymentAdapter", "PaymentEngine", "PaymentIntent", "PaymentResult",
    "FakePaymentAdapter", "InvalidPaymentIntent",
    "CONFIRMED", "PROCESSING", "REJECTED", "STATUSES",
]

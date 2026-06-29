# -*- coding: utf-8 -*-
"""Puerto de Pagos (S2-005) — interfaz `PaymentAdapter` + DTOs.

El Motor de Pago depende EXCLUSIVAMENTE de esta interfaz. Stripe (S2-006) será el
PRIMER adaptador; ni el puerto ni el Motor lo referencian. Cambiar/añadir proveedor
= otro adaptador, sin tocar el Motor ni la vertical.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# Resultado de una autorización/confirmación (vocabulario de negocio, agnóstico del proveedor).
CONFIRMED = "confirmed"     # cobro confirmado
PROCESSING = "processing"   # en proceso (confirmación llegará por webhook)
REJECTED = "rejected"       # rechazado
STATUSES = (CONFIRMED, PROCESSING, REJECTED)


@dataclass(frozen=True)
class PaymentIntent:
    """Intención de cobro. `reference` y `metadata` son OPACOS para el Motor (no los
    interpreta); el monto/idempotencia son lo mínimo que todo proveedor necesita."""
    amount: float
    currency: str
    reference: str
    idempotency_key: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentResult:
    status: str                         # CONFIRMED | PROCESSING | REJECTED
    provider_ref: str | None = None     # id del cobro en el proveedor
    reason: str | None = None           # motivo si REJECTED
    client_action: dict | None = None   # datos OPACOS para el frontend del proveedor (p.ej. client_secret)


class InvalidPaymentIntent(ValueError):
    """La intención de cobro no es válida (p.ej. monto no positivo)."""


class PaymentAdapter(ABC):
    """Contrato que todo proveedor de pago debe implementar."""

    @abstractmethod
    def authorize(self, intent: PaymentIntent) -> PaymentResult:
        """Inicia/autoriza el cobro de una intención → {confirmado/en proceso/rechazado}."""

    @abstractmethod
    def confirm(self, provider_ref: str) -> PaymentResult:
        """Confirma el estado final de un cobro (tras webhook o consulta)."""

    @abstractmethod
    def refund(self, provider_ref: str, amount: float | None = None) -> PaymentResult:
        """Reembolso — STUB en el Sprint 2 (reembolso/disputa self-service está fuera de alcance)."""

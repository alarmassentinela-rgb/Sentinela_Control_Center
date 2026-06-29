# -*- coding: utf-8 -*-
"""Adaptador Stripe (S2-006) — PRIMER PaymentAdapter.

TODA la lógica específica de Stripe vive aquí (y solo aquí). El Motor de Pago no se
toca ni conoce a Stripe. La clave secreta llega por CONFIGURACIÓN (nunca hardcode).

`import stripe` es PEREZOSO (solo en runtime real); en pruebas se inyecta un cliente
fake, de modo que el paquete no es necesario para correr la suite.
"""
from .port import (
    CONFIRMED,
    PROCESSING,
    REJECTED,
    PaymentAdapter,
    PaymentIntent,
    PaymentResult,
)

# Mapea el estado de un PaymentIntent de Stripe al vocabulario de negocio.
_STATUS_MAP = {
    "succeeded": CONFIRMED,
    "processing": PROCESSING,
    "requires_payment_method": PROCESSING,   # falta que el cliente ponga la tarjeta
    "requires_confirmation": PROCESSING,
    "requires_action": PROCESSING,           # 3DS u otra acción del cliente
    "requires_capture": PROCESSING,
    "canceled": REJECTED,
}


def _map_status(stripe_status: str) -> str:
    return _STATUS_MAP.get(stripe_status, PROCESSING)


class StripePaymentAdapter(PaymentAdapter):
    def __init__(self, api_key: str, client=None):
        if not api_key:
            raise ValueError("falta la clave de Stripe (config COC_STRIPE_SECRET_KEY)")
        if client is None:
            import stripe  # perezoso: solo se requiere en runtime real
            client = stripe
        self._client = client
        self._api_key = api_key

    def authorize(self, intent: PaymentIntent) -> PaymentResult:
        try:
            pi = self._client.PaymentIntent.create(
                amount=int(round(intent.amount * 100)),     # Stripe usa la unidad mínima (centavos)
                currency=intent.currency.lower(),
                metadata=dict(intent.metadata, reference=intent.reference),
                idempotency_key=intent.idempotency_key,     # la provee el caso de uso; aquí solo se propaga
                api_key=self._api_key,                      # clave por configuración
            )
        except Exception as e:   # noqa: BLE001 — cualquier fallo del proveedor → rechazado con motivo
            return PaymentResult(status=REJECTED, reason=_reason(e))
        return PaymentResult(
            status=_map_status(pi.status),
            provider_ref=pi.id,
            client_action={"client_secret": pi.client_secret},
        )

    def confirm(self, provider_ref: str) -> PaymentResult:
        pi = self._client.PaymentIntent.retrieve(provider_ref, api_key=self._api_key)
        return PaymentResult(status=_map_status(pi.status), provider_ref=pi.id)

    def refund(self, provider_ref: str, amount: float | None = None) -> PaymentResult:
        # Reembolso fuera de alcance del Sprint 2 (interfaz cumplida; sin implementación).
        raise NotImplementedError("refund fuera de alcance del Sprint 2")


def _reason(exc: Exception) -> str:
    # Stripe expone `user_message`/`code` en sus errores; si no, el texto del error.
    return (getattr(exc, "user_message", None) or getattr(exc, "code", None)
            or str(exc) or "stripe_error")

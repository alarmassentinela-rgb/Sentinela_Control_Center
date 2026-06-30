# -*- coding: utf-8 -*-
"""Webhook de pago — DTO de DOMINIO (S2-008).

El adaptador traduce el webhook del proveedor (formato/firma específicos) a este
DTO agnóstico antes de salir; el caso de uso (router) nunca ve tipos del SDK.
"""
from dataclasses import dataclass

from .port import CONFIRMED, PROCESSING, REJECTED

IGNORED = "ignored"   # evento no relevante para Cobranza (no produce evento de dominio)


@dataclass(frozen=True)
class WebhookEvent:
    provider_event_id: str       # id único del evento del proveedor → idempotencia
    status: str                  # CONFIRMED | REJECTED | PROCESSING | IGNORED
    payment_ref: str | None      # referencia del cobro en el proveedor (PaymentIntent)
    reason: str | None = None


class InvalidWebhookSignature(Exception):
    """La firma del webhook no es válida (traducida a dominio; sin filtrar el SDK)."""

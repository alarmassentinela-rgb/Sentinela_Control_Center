# -*- coding: utf-8 -*-
"""Cascada de Cobranza (S2-015) — ENSAMBLA los consumidores del Sprint 2.

Orquesta la consecuencia de un `pago.confirmado` (spec §5), componiendo capacidades
ya construidas y aprobadas, SIN agregar lógica de negocio nueva:

  pago.confirmado
     → Aplicación de pago (S2-009)  → factura.pagada
        → CFDI async reintetable (S2-010)
        → Reactivation Policy (S2-011)
        → Notificación (S2-012)

Idempotente: si el pago ya fue aplicado, la cascada no repite efectos (se ancla en la
idempotencia de la aplicación de pago). Cada consumidor es además idempotente por su
cuenta. La SPA/el webhook solo disparan; la lógica vive en cada capacidad.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CascadeOutcome:
    applied: bool
    paid_invoice_ids: list[int] = field(default_factory=list)
    notified: bool = False


class CobranzaCascade:
    def __init__(self, application, cfdi, reactivation, notifications):
        self._application = application
        self._cfdi = cfdi
        self._reactivation = reactivation
        self._notifications = notifications

    def on_payment_confirmed(self, payment_id: str) -> CascadeOutcome:
        applied = self._application.apply_confirmed_payment(payment_id)
        if not applied.applied:
            # ya aplicado / nada que hacer → no se repiten efectos (idempotencia)
            return CascadeOutcome(applied=False)

        for inv in applied.paid_invoice_ids:
            self._cfdi.on_factura_pagada(inv)            # async reintetable; nunca invalida el pago
            self._reactivation.on_factura_pagada(inv)    # reactiva por servicio solo si cumple la policy

        self._notifications.on_payment_confirmed(payment_id)   # confirmación al cliente (una vez)
        return CascadeOutcome(applied=True, paid_invoice_ids=list(applied.paid_invoice_ids), notified=True)

# -*- coding: utf-8 -*-
"""Indicadores MVP del Ledger (S2-013).

EXACTAMENTE tres indicadores, calculados SOLO desde el Ledger (los hechos del
AccountingAdapter): **cobrado hoy · cartera vencida · pagos pendientes**. Sin Dashboard
Engine, sin indicadores adicionales, desacoplado de Odoo.
"""
from dataclasses import dataclass
from datetime import date

from .accounting_adapter import PAYMENT, AccountingAdapter


def _parse(d: str | None) -> date | None:
    try:
        return date.fromisoformat(d) if d else None
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True)
class Indicators:
    currency: str
    collected_today: float    # cobrado hoy
    overdue_portfolio: float  # cartera vencida
    pending_payments: float   # pagos pendientes (saldo abierto)

    def as_dict(self) -> dict:
        return {"currency": self.currency, "collected_today": self.collected_today,
                "overdue_portfolio": self.overdue_portfolio, "pending_payments": self.pending_payments}


class LedgerIndicators:
    """Calcula los 3 indicadores desde el AccountingAdapter (no de Odoo directo)."""

    def __init__(self, adapter: AccountingAdapter):
        self._adapter = adapter

    def compute(self, today: date) -> Indicators:
        movs = self._adapter.movements()

        # Cobrado hoy: pagos con fecha de hoy.
        collected_today = sum(m.amount for m in movs if m.kind == PAYMENT and _parse(m.date) == today)

        # Movimientos con saldo pendiente (cargos/notas).
        con_saldo = [m for m in movs if m.amount_residual is not None]
        # Cartera vencida: residual con vencimiento anterior a hoy.
        overdue = 0.0
        for m in con_saldo:
            d = _parse(m.due_date)
            if d is not None and d < today:
                overdue += m.amount_residual
        # Pagos pendientes: saldo abierto total.
        pending = sum(m.amount_residual for m in con_saldo)

        currency = next((m.currency for m in movs if m.currency), "MXN")
        return Indicators(currency, round(collected_today, 2), round(overdue, 2), round(pending, 2))

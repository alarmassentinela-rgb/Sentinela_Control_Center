# -*- coding: utf-8 -*-
"""Ledger — Estado de Cuenta (S2-004).

ÚNICA fuente del Estado de Cuenta: calcula **saldo · vencido · por vencer** a partir
de los HECHOS contables que entrega el `AccountingAdapter`. Toda la lógica financiera
vive aquí (no dispersa en SPA/gateway/Odoo). No duplica la contabilidad: la verdad
sigue en el contable; el Ledger sólo calcula sobre sus hechos.

Convención: sólo los movimientos con `amount_residual` (cargos/notas) afectan el
balance; los pagos ya están netados en ese residual. El signo lo da el contable
(cargos positivos, notas negativas), igual que el resumen probado del Sprint 1.
"""
from dataclasses import dataclass
from datetime import date

from .accounting_adapter import AccountingAdapter


@dataclass(frozen=True)
class AccountStatement:
    currency: str
    balance: float     # saldo total pendiente
    overdue: float     # vencido (residual con vencimiento < hoy)
    upcoming: float    # por vencer (residual con vencimiento >= hoy)

    def as_dict(self) -> dict:
        return {"currency": self.currency, "balance": self.balance,
                "overdue": self.overdue, "upcoming": self.upcoming}


def _parse(d: str | None) -> date | None:
    try:
        return date.fromisoformat(d) if d else None
    except (ValueError, TypeError):
        return None


class Ledger:
    """Calcula el Estado de Cuenta consultando el AccountingAdapter. Depende SÓLO de
    la interfaz del adaptador, nunca del contable concreto."""

    def __init__(self, adapter: AccountingAdapter):
        self._adapter = adapter

    def account_statement(self, today: date, service_id: int | None = None) -> AccountStatement:
        movs = self._adapter.movements(service_id)
        con_saldo = [m for m in movs if m.amount_residual is not None]
        balance = sum(m.amount_residual for m in con_saldo)
        overdue = 0.0
        upcoming = 0.0
        for m in con_saldo:
            d = _parse(m.due_date)
            if d is None:
                continue                    # sin vencimiento: cuenta al saldo, no a vencido/por vencer
            if d < today:
                overdue += m.amount_residual
            else:
                upcoming += m.amount_residual
        currency = next((m.currency for m in movs if m.currency), "MXN")
        return AccountStatement(currency, round(balance, 2), round(overdue, 2), round(upcoming, 2))

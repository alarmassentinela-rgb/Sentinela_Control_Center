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

from .accounting_adapter import CHARGE, AccountingAdapter


@dataclass(frozen=True)
class PaymentReconciliation:
    """Resultado de validar una intención de pago contra el Ledger (S2-007)."""
    ok: bool
    amount: float          # monto esperado según el Ledger (suma de residuales de las facturas)
    currency: str
    reason: str | None = None


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

    def reconcile_payment(self, invoice_ids: list[int], amount: float) -> PaymentReconciliation:
        """Valida una intención de pago contra el Ledger (S2-007): que las facturas
        PERTENEZCAN al cliente (estén entre sus cargos abiertos) y que el monto CUADRE
        con la suma de sus residuales. No aplica nada; solo valida."""
        movs = self._adapter.movements()
        cargos = {m.id: m for m in movs if m.kind == CHARGE and m.amount_residual is not None}
        currency = next((m.currency for m in movs if m.currency), "MXN")
        if not invoice_ids:
            return PaymentReconciliation(False, 0.0, currency, "sin facturas")
        faltantes = [i for i in invoice_ids if i not in cargos]
        if faltantes:
            return PaymentReconciliation(
                False, 0.0, currency,
                "facturas que no pertenecen al cliente o no están abiertas: %s" % faltantes)
        esperado = round(sum(cargos[i].amount_residual for i in invoice_ids), 2)
        if esperado <= 0:
            return PaymentReconciliation(False, esperado, currency, "nada por pagar")
        if round(amount, 2) != esperado:
            return PaymentReconciliation(
                False, esperado, currency,
                "el monto %.2f no cuadra con el Ledger (%.2f)" % (amount, esperado))
        return PaymentReconciliation(True, esperado, currency)

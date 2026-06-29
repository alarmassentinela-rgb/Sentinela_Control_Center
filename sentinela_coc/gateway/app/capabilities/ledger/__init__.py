# -*- coding: utf-8 -*-
"""Capacidad Ledger (Cobranza) — adaptador contable de lectura (S2-003).

El Ledger se construye sobre la contabilidad EXISTENTE vía adaptador; no duplica
la verdad financiera. En S2-004 nace el cálculo del Estado de Cuenta sobre este
adaptador.
"""
from .accounting_adapter import (
    AccountingAdapter,
    AccountingUnavailable,
    FakeAccountingAdapter,
    Movement,
    OdooAccountingAdapter,
    CHARGE,
    PAYMENT,
    NOTE,
)
from .service import AccountStatement, Ledger, PaymentReconciliation

__all__ = [
    "AccountingAdapter", "OdooAccountingAdapter", "FakeAccountingAdapter",
    "Movement", "AccountingUnavailable", "CHARGE", "PAYMENT", "NOTE",
    "Ledger", "AccountStatement", "PaymentReconciliation",
]

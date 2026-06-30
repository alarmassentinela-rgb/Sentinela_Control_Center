# -*- coding: utf-8 -*-
"""Aplicación de pago (S2-009) — consumidor de `pago.confirmado`.

Al confirmarse un pago: registra el pago en el contable (vía un PUERTO de escritura,
NO acoplado a Odoo) → marca factura(s) pagada(s) → publica `factura.pagada`.

Idempotencia + conciliación:
- Solo actúa sobre pagos CONFIRMADOS.
- Si ya existe `factura.pagada` para el pago → no re-aplica (idempotente).
- El puerto contable solo liquida facturas ABIERTAS; las ya pagadas (depósito
  OXXO/banco conciliado) quedan en `already_paid` y NO se les emite `factura.pagada`.
- El `event_id` de `factura.pagada` es estable por (pago, factura) → el Event Store
  deduplica ante reintentos (fail-safe).

NO modifica el Motor de Pago ni el PaymentAdapter. NO conoce a Odoo (solo el puerto).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ApplyResult:
    paid_invoice_ids: list[int]          # facturas que ESTE pago liquidó
    already_paid: list[int] = field(default_factory=list)   # ya estaban pagadas (conciliación)
    created: bool = True                 # False si el pago ya existía en el contable (dedupe por external_ref)


class AccountingPaymentPort(ABC):
    """Puerto de ESCRITURA hacia el contable: registra el pago y lo concilia."""

    @abstractmethod
    def apply_payment(self, partner_id: int, invoice_ids: list[int], amount: float,
                      currency: str, external_ref: str) -> ApplyResult:
        ...


@dataclass(frozen=True)
class ApplyOutcome:
    applied: bool
    paid_invoice_ids: list[int] = field(default_factory=list)
    skipped_reason: str | None = None


class PaymentApplication:
    """Consumidor de `pago.confirmado`. Correlaciona con `pago.iniciado` (mismo
    agregado `payment:<id>`) para conocer facturas/monto, aplica y publica
    `factura.pagada` por cada factura liquidada."""

    def __init__(self, write_port: AccountingPaymentPort, store):
        self._write = write_port
        self._store = store   # CatalogedEventStore

    def apply_confirmed_payment(self, payment_id: str) -> ApplyOutcome:
        eventos = self._store.by_aggregate("payment:%s" % payment_id)
        tipos = {e.type for e in eventos}

        if "pago.confirmado" not in tipos:
            return ApplyOutcome(False, skipped_reason="no_confirmado")   # solo pagos confirmados
        # Idempotencia: ¿ya hay facturas pagadas por ESTE pago? (factura.pagada vive bajo
        # el agregado invoice:<id>, así que se busca por payment_id en el payload).
        ya_aplicado = any(e.payload.get("payment_id") == payment_id
                          for e in self._store.read(type="factura.pagada"))
        if ya_aplicado:
            return ApplyOutcome(False, skipped_reason="ya_aplicado")

        iniciado = next((e for e in eventos if e.type == "pago.iniciado"), None)
        if iniciado is None:
            return ApplyOutcome(False, skipped_reason="sin_intencion")
        p = iniciado.payload
        invoice_ids = list(p.get("invoice_ids") or [])
        amount = p.get("amount") or 0.0
        currency = p.get("currency") or "MXN"
        partner_id = p.get("partner_id")

        res = self._write.apply_payment(partner_id, invoice_ids, amount, currency, external_ref=payment_id)

        for inv in res.paid_invoice_ids:
            self._store.append(
                event_id="factpagada:%s:%s" % (payment_id, inv),   # estable → dedupe ante reintentos
                type="factura.pagada",
                aggregate_id="invoice:%s" % inv,
                payload={"invoice_id": inv, "payment_id": payment_id},
            )
        return ApplyOutcome(True, paid_invoice_ids=list(res.paid_invoice_ids))


class FakeAccountingPayments(AccountingPaymentPort):
    """Para pruebas: liquida lo configurado; registra llamadas."""

    def __init__(self, paid: list[int] | None = None, already_paid: list[int] | None = None,
                 created: bool = True):
        self._paid = paid
        self._already = already_paid or []
        self._created = created
        self.calls: list[tuple] = []

    def apply_payment(self, partner_id, invoice_ids, amount, currency, external_ref) -> ApplyResult:
        self.calls.append((partner_id, tuple(invoice_ids), amount, currency, external_ref))
        paid = self._paid if self._paid is not None else [i for i in invoice_ids if i not in self._already]
        return ApplyResult(paid_invoice_ids=list(paid), already_paid=list(self._already), created=self._created)


class OdooAccountingPayments(AccountingPaymentPort):
    """Implementación real: llama al endpoint INTERNO de Odoo (shared-secret, LAN)
    que crea el pago y lo concilia. Self-contained (no acopla el flujo a Odoo: el
    consumidor solo ve el puerto)."""

    def __init__(self, base_url: str, shared_secret: str):
        self._base = base_url.rstrip("/")
        self._secret = shared_secret

    def apply_payment(self, partner_id, invoice_ids, amount, currency, external_ref) -> ApplyResult:
        import httpx
        payload = {"jsonrpc": "2.0", "method": "call", "params": {
            "partner_id": partner_id, "invoice_ids": invoice_ids, "amount": amount,
            "currency": currency, "external_ref": external_ref}}
        r = httpx.post("%s/coc/internal/payments/apply" % self._base, json=payload,
                       headers={"X-COC-Secret": self._secret}, timeout=20)
        r.raise_for_status()
        res = (r.json() or {}).get("result") or {}
        if not res.get("ok"):
            raise RuntimeError("apply_payment_failed: %s" % res.get("error"))
        return ApplyResult(
            paid_invoice_ids=list(res.get("paid") or []),
            already_paid=list(res.get("already_paid") or []),
            created=bool(res.get("created", True)),
        )

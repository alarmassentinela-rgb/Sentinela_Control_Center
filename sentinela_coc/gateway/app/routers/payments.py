# -*- coding: utf-8 -*-
"""Router de Pagos (S2-007) — intención de pago + endpoint startPayment.

Flujo (NO aplica pagos; eso es S2-008/009):
  1. Valida la intención CONTRA EL LEDGER (facturas del cliente + montos cuadran).
  2. Inicia el cobro vía el Motor de Pago (que solo conoce el PaymentAdapter).
  3. Publica ÚNICAMENTE `pago.iniciado` en el Event Store.

La clave de idempotencia la genera ESTE caso de uso (no el Motor) y se propaga.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .. import deps
from ..capabilities.events import EventStore
from ..capabilities.events.catalog import CatalogedEventStore
from ..capabilities.ledger import AccountingUnavailable, Ledger, OdooAccountingAdapter
from ..capabilities.payments import PaymentEngine, PaymentIntent
from ..clock import utcnow
from ..config import settings

router = APIRouter(prefix="/v1", tags=["payments"])


class StartPaymentIn(BaseModel):
    invoice_ids: list[int]
    amount: float


def get_payment_adapter():
    """Adaptador de pago activo (Stripe en prod). Inyectable/override en pruebas."""
    from ..capabilities.payments.stripe_adapter import StripePaymentAdapter
    return StripePaymentAdapter(settings.stripe_secret_key)


def _meta(request: Request) -> dict:
    return {
        "server_time": utcnow().isoformat() + "Z",
        "request_id": getattr(request.state, "request_id", None)
        or request.headers.get("x-request-id") or "-",
    }


@router.post("/payments/start", summary="Inicia un pago (intención validada contra el Ledger)")
def start_payment(body: StartPaymentIn, request: Request,
                  sess=Depends(deps.current_session), odoo=Depends(deps.get_odoo_client),
                  adapter=Depends(get_payment_adapter), db=Depends(deps.get_db)):
    # 1) Validación contra el Ledger (pertenencia + montos)
    ledger = Ledger(OdooAccountingAdapter(odoo, sess.odoo_session_id))
    try:
        recon = ledger.reconcile_payment(body.invoice_ids, body.amount)
    except AccountingUnavailable as e:
        if e.status in (301, 302, 303, 401):
            raise HTTPException(status_code=401, detail="session_expired")
        raise HTTPException(status_code=502, detail="accounting_unavailable")
    if not recon.ok:
        # Rechazo CLARO si las facturas/montos no cuadran (no se inicia cobro).
        raise HTTPException(status_code=422, detail=recon.reason)

    # 2) Iniciar el cobro vía el Motor de Pago
    idempotency_key = uuid.uuid4().hex   # la provee el caso de uso, no el Motor
    intent = PaymentIntent(
        amount=recon.amount, currency=recon.currency,
        reference=",".join(str(i) for i in body.invoice_ids),
        idempotency_key=idempotency_key,
        metadata={"partner_id": sess.partner_id, "invoice_ids": body.invoice_ids},
    )
    result = PaymentEngine(adapter).authorize(intent)

    # 3) Publicar ÚNICAMENTE pago.iniciado (no se aplica el pago aquí)
    payment_id = result.provider_ref or idempotency_key
    CatalogedEventStore(EventStore(db)).append(
        event_id=uuid.uuid4().hex,
        type="pago.iniciado",
        aggregate_id="payment:%s" % payment_id,
        payload={
            "payment_id": payment_id,
            "partner_id": sess.partner_id,
            "invoice_ids": body.invoice_ids,
            "amount": recon.amount,
            "currency": recon.currency,
            "status": result.status,
            "provider_ref": result.provider_ref,
        },
    )

    return {
        "data": {
            "payment_id": payment_id,
            "status": result.status,
            "provider_ref": result.provider_ref,
            "amount": recon.amount,
            "currency": recon.currency,
            "client_action": result.client_action,
        },
        "meta": _meta(request),
    }

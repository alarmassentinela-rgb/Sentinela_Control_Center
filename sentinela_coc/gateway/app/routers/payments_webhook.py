# -*- coding: utf-8 -*-
"""Webhook de confirmación de pago (S2-008).

Recibe el webhook del proveedor (endpoint público; se autentica por FIRMA, no por
sesión). La verificación de firma y la traducción a dominio ocurren en el ADAPTADOR.
Aquí (caso de uso) solo se publica ÚNICAMENTE `pago.confirmado` o `pago.rechazado`,
de forma IDEMPOTENTE (dedupe por el id del evento del proveedor en el Event Store).

NO aplica el pago contable (eso es S2-009). No toca el Ledger.
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from .. import deps
from ..capabilities.events import EventStore
from ..capabilities.events.catalog import CatalogedEventStore
from ..capabilities.payments import CONFIRMED, REJECTED
from ..capabilities.payments.webhook import InvalidWebhookSignature
from .payments import get_payment_adapter

router = APIRouter(prefix="/v1", tags=["payments"])

_EVENT_BY_STATUS = {CONFIRMED: "pago.confirmado", REJECTED: "pago.rechazado"}


@router.post("/payments/webhook", summary="Webhook de pago (firma verificada, idempotente)")
async def payment_webhook(request: Request, adapter=Depends(get_payment_adapter), db=Depends(deps.get_db)):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        ev = adapter.parse_webhook(payload, signature)   # verifica firma + traduce a dominio
    except InvalidWebhookSignature:
        raise HTTPException(status_code=400, detail="invalid_signature")

    etype = _EVENT_BY_STATUS.get(ev.status)
    if etype is None:
        # en proceso / no relevante: aceptado, sin publicar evento de dominio
        return {"ok": True, "published": False, "status": ev.status}

    # Idempotencia: el event_id = id del evento del proveedor. Un webhook duplicado
    # produce el mismo event_id → el Event Store no lo inserta dos veces.
    res = CatalogedEventStore(EventStore(db)).append(
        event_id=ev.provider_event_id,
        type=etype,
        aggregate_id="payment:%s" % ev.payment_ref,
        payload={"payment_id": ev.payment_ref, "status": ev.status, "reason": ev.reason},
    )
    return {"ok": True, "published": res.created, "type": etype}

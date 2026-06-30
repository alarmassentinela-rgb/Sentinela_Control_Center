# -*- coding: utf-8 -*-
"""Webhook de confirmación de pago (S2-008).

Recibe el webhook del proveedor (endpoint público; se autentica por FIRMA, no por
sesión). La verificación de firma y la traducción a dominio ocurren en el ADAPTADOR.
Aquí (caso de uso) solo se publica ÚNICAMENTE `pago.confirmado` o `pago.rechazado`,
de forma IDEMPOTENTE (dedupe por el id del evento del proveedor en el Event Store).

NO aplica el pago contable (eso es S2-009). No toca el Ledger.
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from fastapi import Depends

from .. import deps
from ..capabilities.events import EventStore
from ..capabilities.events.catalog import CatalogedEventStore
from ..capabilities.payments import CONFIRMED, REJECTED
from ..capabilities.payments.webhook import InvalidWebhookSignature
from ..config import settings
from .payments import get_payment_adapter

router = APIRouter(prefix="/v1", tags=["payments"])

_EVENT_BY_STATUS = {CONFIRMED: "pago.confirmado", REJECTED: "pago.rechazado"}


def get_cobranza_cascade(db=Depends(deps.get_db)):
    """Ensambla la cascada de Cobranza con los puertos reales de Odoo (S2-015).
    Inyectable/override en pruebas."""
    from ..capabilities.cfdi import CfdiConsumer, OdooCfdiPort
    from ..capabilities.cobranza import CobranzaCascade
    from ..capabilities.notifications import NotificationsConsumer, OdooNotificationChannel
    from ..capabilities.payments.application import OdooAccountingPayments, PaymentApplication
    from ..capabilities.reactivation import OdooReactivationPort, ReactivationPolicy

    store = CatalogedEventStore(EventStore(db))
    base, secret = settings.odoo_base_url, settings.coc_shared_secret
    return CobranzaCascade(
        application=PaymentApplication(OdooAccountingPayments(base, secret), store),
        cfdi=CfdiConsumer(OdooCfdiPort(base, secret)),
        reactivation=ReactivationPolicy(OdooReactivationPort(base, secret), store),
        notifications=NotificationsConsumer(OdooNotificationChannel(base, secret), store),
    )


@router.post("/payments/webhook", summary="Webhook de pago (firma verificada, idempotente)")
async def payment_webhook(request: Request, adapter=Depends(get_payment_adapter),
                          cascade=Depends(get_cobranza_cascade), db=Depends(deps.get_db)):
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

    # Ensamblado (S2-015): al confirmar (y solo en la 1ª publicación), dispara la cascada
    # de Cobranza. Fail-safe: un fallo aquí NO rompe el webhook (es reintetable).
    if etype == "pago.confirmado" and res.created:
        try:
            cascade.on_payment_confirmed(ev.payment_ref)
        except Exception:  # noqa: BLE001
            pass

    return {"ok": True, "published": res.created, "type": etype}

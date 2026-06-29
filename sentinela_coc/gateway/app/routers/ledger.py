# -*- coding: utf-8 -*-
"""Router del Ledger (S2-004) — sirve el Estado de Cuenta calculado por el Ledger.

Thin: arma el adaptador Odoo sobre la sesión efímera del cliente y delega el cálculo
en el Ledger (única fuente). Solo lectura. Envoltura {data, meta} como el resto del BFF.
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from .. import deps
from ..capabilities.ledger import AccountingUnavailable, Ledger, OdooAccountingAdapter
from ..clock import utcnow

router = APIRouter(prefix="/v1", tags=["ledger"])


@router.get("/ledger/statement", summary="Estado de Cuenta (desde el Ledger)")
def statement(request: Request, service_id: int | None = None,
              sess=Depends(deps.current_session), odoo=Depends(deps.get_odoo_client)):
    adapter = OdooAccountingAdapter(odoo, sess.odoo_session_id)
    try:
        st = Ledger(adapter).account_statement(today=utcnow().date(), service_id=service_id)
    except AccountingUnavailable as e:
        if e.status in (301, 302, 303, 401):
            raise HTTPException(status_code=401, detail="session_expired")
        raise HTTPException(status_code=502, detail="accounting_unavailable")
    return {
        "data": st.as_dict(),
        "meta": {
            "server_time": utcnow().isoformat() + "Z",
            "request_id": getattr(request.state, "request_id", None)
            or request.headers.get("x-request-id") or "-",
        },
    }

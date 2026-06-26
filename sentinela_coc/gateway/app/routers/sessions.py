# -*- coding: utf-8 -*-
"""Centro de sesiones activas + historial de accesos (W5.5 / W5.9)."""
from fastapi import APIRouter, Depends, Request, Response, status

from .. import deps
from ..services import audit, session_service

router = APIRouter(prefix="/v1", tags=["sessions"])


def _ip(r: Request):
    return r.headers.get("x-forwarded-for") or (r.client.host if r.client else None)


def _ua(r: Request):
    return r.headers.get("user-agent")


@router.get("/sessions")
def list_sessions(sess=Depends(deps.current_session), db=Depends(deps.get_db)):
    rows = session_service.list_active_sessions(db, sess.partner_id)
    return {"sessions": [session_service.serialize_session(s, current_sid=sess.id) for s in rows]}


@router.delete("/sessions/{sid}")
def close_session(sid: str, request: Request, response: Response,
                  sess=Depends(deps.current_session), db=Depends(deps.get_db),
                  odoo=Depends(deps.get_odoo_client)):
    ok = session_service.close_session_by_id(db, odoo, sess.partner_id, sid, ip=_ip(request), ua=_ua(request))
    if not ok:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"ok": False, "error": "not_found"}
    return {"ok": True}


@router.post("/sessions/close-all")
def close_all(request: Request, sess=Depends(deps.current_session), db=Depends(deps.get_db),
              odoo=Depends(deps.get_odoo_client)):
    n = session_service.close_all_for_partner(db, odoo, sess.partner_id, except_sid=sess.id,
                                              ip=_ip(request), ua=_ua(request))
    return {"ok": True, "closed": n}


@router.get("/access-history")
def access_history(sess=Depends(deps.current_session), db=Depends(deps.get_db),
                   limit: int = 50, offset: int = 0):
    rows = audit.list_history(db, sess.partner_id, limit=min(limit, 200), offset=offset)
    return {"events": [{
        "event_type": e.event_type, "success": e.success, "ip": e.ip, "device": e.device,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    } for e in rows]}

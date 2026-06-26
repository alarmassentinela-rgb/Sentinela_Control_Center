# -*- coding: utf-8 -*-
"""Centro de dispositivos confiables (W5.9)."""
from fastapi import APIRouter, Depends, Response, status

from .. import deps
from ..services import device_service

router = APIRouter(prefix="/v1/devices", tags=["devices"])


@router.get("")
def list_devices(sess=Depends(deps.current_session), db=Depends(deps.get_db)):
    return {"devices": [device_service.serialize_device(d)
                        for d in device_service.list_devices(db, sess.identity_id)]}


@router.post("/{device_pk}/trust")
def trust(device_pk: str, response: Response, sess=Depends(deps.current_session), db=Depends(deps.get_db)):
    d = device_service.set_trust(db, sess.identity_id, device_pk, True)
    if not d:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "trusted": True}


@router.delete("/{device_pk}/trust")
def untrust(device_pk: str, response: Response, sess=Depends(deps.current_session), db=Depends(deps.get_db)):
    d = device_service.set_trust(db, sess.identity_id, device_pk, False)
    if not d:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "trusted": False}


@router.delete("/{device_pk}")
def remove(device_pk: str, response: Response, sess=Depends(deps.current_session),
           db=Depends(deps.get_db), odoo=Depends(deps.get_odoo_client)):
    ok = device_service.remove_device(db, odoo, sess.identity_id, device_pk)
    if not ok:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"ok": False, "error": "not_found"}
    return {"ok": True}

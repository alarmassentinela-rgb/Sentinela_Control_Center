# -*- coding: utf-8 -*-
"""Magic Links de un solo uso (W5.10) — consumo público + emisión interna."""
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel

from .. import deps
from ..config import settings
from ..services import magic_service

public = APIRouter(prefix="/v1/magic", tags=["magic"])
internal = APIRouter(prefix="/coc/internal/magic", tags=["internal"])


class ConsumeIn(BaseModel):
    token: str


class IssueIn(BaseModel):
    purpose: str
    partner_id: int
    res_model: str | None = None
    res_id: int | None = None
    ttl_sec: int = 600


def _verify_internal_secret(x_coc_secret: str | None = Header(default=None)):
    if (not settings.coc_shared_secret or not x_coc_secret
            or not hmac.compare_digest(x_coc_secret, settings.coc_shared_secret)):
        raise HTTPException(status_code=403, detail="forbidden")


@public.post("/consume")
def consume(body: ConsumeIn, request: Request, response: Response, db=Depends(deps.get_db)):
    r = magic_service.consume(db, body.token,
                              ip=request.headers.get("x-forwarded-for") or (request.client.host if request.client else None),
                              ua=request.headers.get("user-agent"))
    if not r.get("ok"):
        response.status_code = status.HTTP_400_BAD_REQUEST
    return r


@internal.post("/issue", dependencies=[Depends(_verify_internal_secret)])
def issue(body: IssueIn, db=Depends(deps.get_db)):
    raw = magic_service.issue(db, body.purpose, body.partner_id, body.res_model, body.res_id, body.ttl_sec)
    return {"ok": True, "token": raw}

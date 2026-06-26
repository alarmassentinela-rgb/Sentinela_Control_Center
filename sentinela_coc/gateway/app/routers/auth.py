# -*- coding: utf-8 -*-
"""Endpoints de autenticación del Portal (W5.3/W5.4).

POST /v1/auth/otp/request · /otp/verify · /refresh · /logout
Identidad por OTP; el aislamiento lo aplica Odoo (record rules) vía sesión efímera.
"""
from fastapi import APIRouter, Depends, Header, Request, Response, status
from pydantic import BaseModel

from .. import deps
from ..config import settings
from ..security.tokens import decode_access_token
from ..services import otp_service, session_service

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class OtpRequestIn(BaseModel):
    phone: str
    device: str | None = None
    channel: str = "whatsapp"


class OtpVerifyIn(BaseModel):
    phone: str
    code: str
    device: str | None = None


class RefreshIn(BaseModel):
    refresh_token: str


def _ip(request: Request):
    return request.headers.get("x-forwarded-for") or (request.client.host if request.client else None)


def _ua(request: Request):
    return request.headers.get("user-agent")


def _device(request: Request, body_device):
    return body_device or request.headers.get("x-device-id")


@router.post("/otp/request")
def otp_request(body: OtpRequestIn, request: Request, response: Response,
                db=Depends(deps.get_db), provider=Depends(deps.get_otp_provider)):
    r = otp_service.request_otp(db, provider, body.phone, _ip(request), _device(request, body.device), body.channel)
    if not r.get("ok"):
        response.status_code = status.HTTP_429_TOO_MANY_REQUESTS
        return {"ok": False, "error": r.get("reason")}
    return {"ok": True}  # neutral (no revela si el teléfono existe)


@router.post("/otp/verify")
def otp_verify(body: OtpVerifyIn, request: Request, response: Response,
               db=Depends(deps.get_db), odoo=Depends(deps.get_odoo_client),
               notifier=Depends(deps.get_notifier)):
    r = otp_service.verify_otp(db, odoo, body.phone, body.code, _ip(request),
                               _device(request, body.device), _ua(request), notifier=notifier)
    if r.get("ok"):
        return {k: v for k, v in r.items() if k != "ok"}
    response.status_code = (status.HTTP_429_TOO_MANY_REQUESTS if r.get("error") == "rate"
                            else status.HTTP_401_UNAUTHORIZED)
    return {"ok": False, "error": r.get("error", "invalid")}


@router.post("/refresh")
def refresh(body: RefreshIn, request: Request, response: Response,
            db=Depends(deps.get_db), odoo=Depends(deps.get_odoo_client)):
    r = session_service.refresh_session(db, odoo, body.refresh_token, _ip(request), _ua(request))
    if r.get("ok"):
        return {k: v for k, v in r.items() if k != "ok"}
    response.status_code = status.HTTP_401_UNAUTHORIZED
    return {"ok": False, "error": r.get("error", "invalid")}


@router.post("/logout")
def logout(request: Request, response: Response, db=Depends(deps.get_db),
           odoo=Depends(deps.get_odoo_client), authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"ok": False, "error": "no_token"}
    try:
        claims = decode_access_token(authorization.split(" ", 1)[1], settings.jwt_secret)
    except Exception:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"ok": False, "error": "invalid_token"}
    sess = session_service.get_session(db, claims.get("sid"))
    session_service.revoke_session(db, odoo, sess, event="logout", ip=_ip(request), ua=_ua(request))
    return {"ok": True}

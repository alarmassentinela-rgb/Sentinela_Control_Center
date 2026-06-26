# -*- coding: utf-8 -*-
"""Endpoints de autenticación del Portal (W5.3/W5.4).

POST /v1/auth/otp/request · /otp/verify · /refresh · /logout
Identidad por OTP; el aislamiento lo aplica Odoo (record rules) vía sesión efímera.
"""
from fastapi import APIRouter, Depends, Header, Request, Response, status
from pydantic import BaseModel

from .. import deps
from ..config import settings
from ..models import PortalIdentity
from ..security.tokens import decode_access_token
from ..services import otp_service, password_service, phone_change_service, session_service

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


# ---------------------------------------------------------------------------
# W5.8 — contraseña, recuperación y cambio de teléfono
# ---------------------------------------------------------------------------
class PasswordSetIn(BaseModel):
    new_password: str
    current_password: str | None = None


class PasswordLoginIn(BaseModel):
    phone: str
    password: str
    device: str | None = None


class RecoverRequestIn(BaseModel):
    phone: str
    device: str | None = None


class RecoverConfirmIn(BaseModel):
    phone: str
    code: str
    new_password: str
    device: str | None = None


class PhoneChangeRequestIn(BaseModel):
    new_phone: str


class PhoneChangeConfirmIn(BaseModel):
    new_phone: str
    code_new: str
    code_current: str | None = None


def _identity(db, sess):
    return db.query(PortalIdentity).filter_by(id=sess.identity_id).one_or_none()


@router.post("/password")
def set_password(body: PasswordSetIn, request: Request, response: Response,
                 sess=Depends(deps.current_session), db=Depends(deps.get_db), odoo=Depends(deps.get_odoo_client)):
    r = password_service.set_or_change_password(
        db, odoo, _identity(db, sess), body.new_password, body.current_password,
        keep_session_id=sess.id, ip=_ip(request), ua=_ua(request))
    if not r.get("ok"):
        response.status_code = status.HTTP_400_BAD_REQUEST
    return r


@router.post("/password/login")
def password_login(body: PasswordLoginIn, request: Request, response: Response,
                   db=Depends(deps.get_db), odoo=Depends(deps.get_odoo_client), notifier=Depends(deps.get_notifier)):
    r = password_service.login_password(db, odoo, body.phone, body.password, _ip(request),
                                        _device(request, body.device), _ua(request), notifier=notifier)
    if r.get("ok"):
        return {k: v for k, v in r.items() if k != "ok"}
    response.status_code = status.HTTP_401_UNAUTHORIZED
    return {"ok": False, "error": r.get("error", "invalid")}


@router.post("/recover/request")
def recover_request(body: RecoverRequestIn, request: Request,
                    db=Depends(deps.get_db), provider=Depends(deps.get_otp_provider)):
    password_service.recover_request(db, provider, body.phone, _ip(request), _device(request, body.device))
    return {"ok": True}   # neutral


@router.post("/recover/confirm")
def recover_confirm(body: RecoverConfirmIn, request: Request, response: Response,
                    db=Depends(deps.get_db), odoo=Depends(deps.get_odoo_client)):
    r = password_service.recover_confirm(db, odoo, body.phone, body.code, body.new_password,
                                         _ip(request), _device(request, body.device), _ua(request))
    if not r.get("ok"):
        response.status_code = status.HTTP_400_BAD_REQUEST
    return r


@router.post("/phone/change/request")
def phone_change_request(body: PhoneChangeRequestIn, request: Request,
                         sess=Depends(deps.current_session), db=Depends(deps.get_db),
                         provider=Depends(deps.get_otp_provider)):
    return phone_change_service.request_change(db, provider, _identity(db, sess), body.new_phone, _ip(request), None)


@router.post("/phone/change/confirm")
def phone_change_confirm(body: PhoneChangeConfirmIn, request: Request, response: Response,
                         sess=Depends(deps.current_session), db=Depends(deps.get_db),
                         odoo=Depends(deps.get_odoo_client)):
    r = phone_change_service.confirm_change(db, odoo, _identity(db, sess), body.new_phone,
                                            body.code_new, body.code_current, _ip(request), None, _ua(request))
    if not r.get("ok"):
        response.status_code = status.HTTP_400_BAD_REQUEST
    return r

# -*- coding: utf-8 -*-
"""Modelos de datos del Gateway (W5.1).

Diseño de autenticación: sesiones de VIDA CORTA, sin credenciales permanentes.
- PortalIdentity: teléfono/email -> partner_id de Odoo.
- PortalSession: sesión del cliente (access corto + refresh rotativo + revocación);
  guarda el id de la SESIÓN ODOO EFÍMERA (no una API key permanente).
- OtpChallenge: reto OTP (single-use, TTL, rate-limit).
- AuthAuditEvent: auditoría completa de autenticación.
- MagicLinkToken: token de UN SOLO USO para firma/autorizaciones.

El aislamiento de datos NO depende de estas tablas: lo garantizan las record rules
de Odoo (WS-2). Aquí solo vive *quién* es el cliente y el ciclo de su sesión.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class PortalIdentity(Base):
    __tablename__ = "portal_identity"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    partner_id: Mapped[int] = mapped_column(Integer, index=True)  # Odoo res.partner
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(254), index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))  # argon2; opcional
    status: Mapped[str] = mapped_column(String(16), default="active")  # active/blocked
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sessions: Mapped[list["PortalSession"]] = relationship(back_populates="identity")


class PortalSession(Base):
    __tablename__ = "portal_session"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    identity_id: Mapped[str] = mapped_column(
        ForeignKey("portal_identity.id", ondelete="CASCADE"), index=True
    )
    partner_id: Mapped[int] = mapped_column(Integer, index=True)

    # Autorización en Odoo: SESIÓN ODOO EFÍMERA (no API key permanente).
    odoo_uid: Mapped[int | None] = mapped_column(Integer)
    odoo_session_id: Mapped[str | None] = mapped_column(String(255))

    # Access JWT (corto) — se referencia por jti para revocación inmediata.
    access_jti: Mapped[str | None] = mapped_column(String(32), index=True)

    # Refresh token: opaco, ROTATIVO, hasheado. La familia permite detectar reuse.
    refresh_hash: Mapped[str | None] = mapped_column(String(255), index=True)
    refresh_family: Mapped[str] = mapped_column(String(32), default=_uuid, index=True)
    refresh_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Dispositivo / contexto
    device_label: Mapped[str | None] = mapped_column(String(120))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(400))

    # Ciclo de vida / revocación
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    identity: Mapped["PortalIdentity"] = relationship(back_populates="sessions")


class OtpChallenge(Base):
    __tablename__ = "otp_challenge"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    channel: Mapped[str] = mapped_column(String(16), default="whatsapp")  # whatsapp/sms
    code_hash: Mapped[str] = mapped_column(String(255))  # nunca el código en claro
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)  # single-use
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthAuditEvent(Base):
    __tablename__ = "auth_audit_event"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    # otp_request / otp_verify / login / refresh / logout / revoke / revoke_all /
    # magic_link_use / blocked
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    partner_id: Mapped[int | None] = mapped_column(Integer, index=True)
    identity_id: Mapped[str | None] = mapped_column(String(32), index=True)
    session_id: Mapped[str | None] = mapped_column(String(32), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(400))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class MagicLinkToken(Base):
    __tablename__ = "magic_link_token"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(24))  # sign_document / authorize_service
    partner_id: Mapped[int | None] = mapped_column(Integer, index=True)
    res_model: Mapped[str | None] = mapped_column(String(64))
    res_id: Mapped[int | None] = mapped_column(Integer)
    used: Mapped[bool] = mapped_column(Boolean, default=False)  # UN SOLO USO
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

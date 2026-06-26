# -*- coding: utf-8 -*-
"""Modelos de datos del Gateway (sesiones cortas, sin credenciales permanentes).

Fechas en UTC naïve (datetime.utcnow) para portabilidad SQLite(tests)↔Postgres(prod).
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .clock import utcnow
from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class PortalIdentity(Base):
    __tablename__ = "portal_identity"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    partner_id: Mapped[int] = mapped_column(Integer, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(254), index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    sessions: Mapped[list["PortalSession"]] = relationship(back_populates="identity")


class PortalSession(Base):
    __tablename__ = "portal_session"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    identity_id: Mapped[str] = mapped_column(ForeignKey("portal_identity.id", ondelete="CASCADE"), index=True)
    partner_id: Mapped[int] = mapped_column(Integer, index=True)

    odoo_uid: Mapped[int | None] = mapped_column(Integer)
    odoo_session_id: Mapped[str | None] = mapped_column(String(255))

    access_jti: Mapped[str | None] = mapped_column(String(32), index=True)
    refresh_family: Mapped[str] = mapped_column(String(32), default=_uuid, index=True)

    device_id: Mapped[str | None] = mapped_column(String(120), index=True)   # fingerprint del cliente
    device_label: Mapped[str | None] = mapped_column(String(120))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(400))

    revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    identity: Mapped["PortalIdentity"] = relationship(back_populates="sessions")


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("portal_session.id", ondelete="CASCADE"), index=True)
    family: Mapped[str] = mapped_column(String(32), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Device(Base):
    __tablename__ = "trusted_device"
    __table_args__ = (UniqueConstraint("identity_id", "device_id", name="uq_identity_device"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    identity_id: Mapped[str] = mapped_column(ForeignKey("portal_identity.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str] = mapped_column(String(120), index=True)   # fingerprint del cliente
    label: Mapped[str | None] = mapped_column(String(120))
    trusted: Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_ip: Mapped[str | None] = mapped_column(String(64))
    last_user_agent: Mapped[str | None] = mapped_column(String(400))


class OtpChallenge(Base):
    __tablename__ = "otp_challenge"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    channel: Mapped[str] = mapped_column(String(16), default="whatsapp")
    code_hash: Mapped[str] = mapped_column(String(255))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    device: Mapped[str | None] = mapped_column(String(120))
    ip: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuthAuditEvent(Base):
    __tablename__ = "auth_audit_event"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    partner_id: Mapped[int | None] = mapped_column(Integer, index=True)
    identity_id: Mapped[str | None] = mapped_column(String(32), index=True)
    session_id: Mapped[str | None] = mapped_column(String(32), index=True)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    device: Mapped[str | None] = mapped_column(String(120), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    ip: Mapped[str | None] = mapped_column(String(64), index=True)
    user_agent: Mapped[str | None] = mapped_column(String(400))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class MagicLinkToken(Base):
    __tablename__ = "magic_link_token"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(24))
    partner_id: Mapped[int | None] = mapped_column(Integer, index=True)
    res_model: Mapped[str | None] = mapped_column(String(64))
    res_id: Mapped[int | None] = mapped_column(Integer)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

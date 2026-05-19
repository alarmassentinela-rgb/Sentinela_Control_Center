import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    gender: Mapped[Optional[str]] = mapped_column(String(10))
    birthdate: Mapped[Optional[date]] = mapped_column(Date)
    country: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    # Hándicap
    initial_handicap: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))
    handicap_index: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))
    handicap_last_updated: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    handicap_rounds_count: Mapped[int] = mapped_column(Integer, default=0)
    # Suscripción
    plan_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("subscription_plans.id"))
    plan_expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    # Estado
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_inapp: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class PushToken(Base):
    __tablename__ = "push_tokens"
    __table_args__ = (UniqueConstraint("user_id", "token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[Optional[str]] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

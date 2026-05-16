import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Numeric, Text, ForeignKey, UniqueConstraint, Date
from sqlalchemy.dialects.postgresql import JSONB, UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from app.models.base import Base


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500))
    cover_url: Mapped[Optional[str]] = mapped_column(String(500))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    website: Mapped[Optional[str]] = mapped_column(String(300))
    instagram: Mapped[Optional[str]] = mapped_column(String(200))
    facebook: Mapped[Optional[str]] = mapped_column(String(200))
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    timezone: Mapped[str] = mapped_column(String(100), default="America/Mexico_City")
    plan_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("subscription_plans.id"))
    plan_expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # ─── Política de acceso (Clubs SaaS Fase 4 — Híbrido) ──────────────────
    access_type: Mapped[str] = mapped_column(String(20), default="private")  # private|semi_private|public
    allow_guests: Mapped[bool] = mapped_column(Boolean, default=True)
    guest_requires_sponsor: Mapped[bool] = mapped_column(Boolean, default=True)
    max_guests_per_booking: Mapped[int] = mapped_column(Integer, default=3)
    max_guest_visits_per_year: Mapped[int] = mapped_column(Integer, default=6)
    guest_fee_to_sponsor: Mapped[bool] = mapped_column(Boolean, default=True)
    members_advance_days: Mapped[int] = mapped_column(Integer, default=30)
    public_advance_days: Mapped[int] = mapped_column(Integer, default=7)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class ClubStaff(Base):
    __tablename__ = "club_staff"
    __table_args__ = (UniqueConstraint("club_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    club_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[Optional[str]] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class MembershipType(Base):
    __tablename__ = "membership_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    club_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    monthly_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    yearly_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    benefits: Mapped[Optional[dict]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class ClubMember(Base):
    __tablename__ = "club_members"
    __table_args__ = (UniqueConstraint("club_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    membership_type_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("membership_types.id"))
    member_number: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="active")
    joined_at: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class MemberAccount(Base):
    __tablename__ = "member_accounts"
    __table_args__ = (UniqueConstraint("club_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("clubs.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id"))
    balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    credit_limit: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class AccountTransaction(Base):
    __tablename__ = "account_transactions"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("member_accounts.id"))
    type: Mapped[Optional[str]] = mapped_column(String(30))
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True))
    reference_type: Mapped[Optional[str]] = mapped_column(String(50))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

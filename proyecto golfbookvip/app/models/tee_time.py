import uuid
from datetime import datetime, date, time
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Numeric, Text, ForeignKey, UniqueConstraint, Date, Time
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from app.models.base import Base


class TeeTimeSlot(Base):
    __tablename__ = "tee_time_slots"
    __table_args__ = (UniqueConstraint("club_id", "date", "time", name="tee_time_slots_club_date_time_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    club_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"))
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[time] = mapped_column(Time, nullable=False)
    max_players: Mapped[int] = mapped_column(Integer, default=4)
    available_spots: Mapped[int] = mapped_column(Integer, default=4)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason: Mapped[Optional[str]] = mapped_column(String(200))
    # ─── Tier + pricing (Fase 4.2 — Híbrido) ───────────────────────────────
    tier: Mapped[str] = mapped_column(String(20), default="members_only")  # members_only | members_priority | public
    green_fee_member: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    green_fee_guest: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    green_fee_public: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class TeeTimeBooking(Base):
    __tablename__ = "tee_time_bookings"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slot_id: Mapped[int] = mapped_column(Integer, ForeignKey("tee_time_slots.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id"))
    players_count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    booked_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    reminder_24h_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_1h_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TeeTimeBookingPlayer(Base):
    """Jugadores individuales por booking. v1.17.0 reemplaza el contador players_count con detalle por jugador."""
    __tablename__ = "tee_time_booking_players"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("tee_time_bookings.id", ondelete="CASCADE"))
    player_type: Mapped[str] = mapped_column(String(20))  # member | guest | public
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    guest_name: Mapped[Optional[str]] = mapped_column(String(200))
    guest_email: Mapped[Optional[str]] = mapped_column(String(255))
    sponsor_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    fee_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    added_by: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

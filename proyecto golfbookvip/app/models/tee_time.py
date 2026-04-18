import uuid
from datetime import datetime, date, time
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, UniqueConstraint, Date, Time
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from app.models.base import Base


class TeeTimeSlot(Base):
    __tablename__ = "tee_time_slots"
    __table_args__ = (UniqueConstraint("course_id", "date", "time"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[time] = mapped_column(Time, nullable=False)
    max_players: Mapped[int] = mapped_column(Integer, default=4)
    available_spots: Mapped[int] = mapped_column(Integer, default=4)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason: Mapped[Optional[str]] = mapped_column(String(200))
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

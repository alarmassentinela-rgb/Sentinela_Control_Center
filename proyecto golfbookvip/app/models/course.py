import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Numeric, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from app.models.base import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("clubs.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    country: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(Text)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 8))
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(11, 8))
    cover_url: Mapped[Optional[str]] = mapped_column(String(500))
    holes_count: Mapped[int] = mapped_column(Integer, default=18, nullable=True)
    par_total: Mapped[Optional[int]] = mapped_column(Integer)
    course_rating: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))
    slope_rating: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class CourseHole(Base):
    __tablename__ = "course_holes"
    __table_args__ = (UniqueConstraint("course_id", "hole_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=True)
    hole_number: Mapped[int] = mapped_column(Integer, nullable=False)
    par: Mapped[int] = mapped_column(Integer, nullable=False)
    stroke_index: Mapped[Optional[int]] = mapped_column(Integer)
    distance_meters: Mapped[Optional[int]] = mapped_column(Integer)
    distance_yards: Mapped[Optional[int]] = mapped_column(Integer)
    distance_yards_black: Mapped[Optional[int]] = mapped_column(Integer)
    distance_yards_blue: Mapped[Optional[int]] = mapped_column(Integer)
    distance_yards_white: Mapped[Optional[int]] = mapped_column(Integer)
    distance_yards_red: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    # GPS general (deprecated — usar tee_* y green_*)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 8))
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(11, 8))
    # GPS específico — centro del green (para distancia al pin)
    green_latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 8))
    green_longitude: Mapped[Optional[float]] = mapped_column(Numeric(11, 8))
    # GPS específico — tee de salida
    tee_latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 8))
    tee_longitude: Mapped[Optional[float]] = mapped_column(Numeric(11, 8))

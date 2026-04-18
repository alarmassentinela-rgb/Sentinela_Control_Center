import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Numeric, ForeignKey, Date
from sqlalchemy.dialects.postgresql import JSONB, UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from app.models.base import Base


class ScoreDifferential(Base):
    __tablename__ = "score_differentials"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    round_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("rounds.id", ondelete="SET NULL"))
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("courses.id"))
    adjusted_gross_score: Mapped[int] = mapped_column(Integer, nullable=False)
    course_rating: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    slope_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    differential: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    pcc_adjustment: Mapped[float] = mapped_column(Numeric(4, 2), default=0)
    exceptional_reduction: Mapped[float] = mapped_column(Numeric(4, 2), default=0)
    is_nine_hole: Mapped[bool] = mapped_column(Boolean, default=False)
    expected_score_adjustment: Mapped[float] = mapped_column(Numeric(4, 2), default=0)
    is_counting: Mapped[bool] = mapped_column(Boolean, default=True)
    played_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class HandicapHistory(Base):
    __tablename__ = "handicap_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    handicap_index: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    previous_index: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))
    differentials_used: Mapped[Optional[dict]] = mapped_column(JSONB)
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    rounds_counted: Mapped[Optional[int]] = mapped_column(Integer)
    soft_cap_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    hard_cap_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class PlayerStats(Base):
    __tablename__ = "player_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    total_rounds: Mapped[int] = mapped_column(Integer, default=0)
    total_holes: Mapped[int] = mapped_column(Integer, default=0)
    avg_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    avg_putts_per_round: Mapped[Optional[float]] = mapped_column(Numeric(4, 2))
    avg_putts_per_hole: Mapped[Optional[float]] = mapped_column(Numeric(4, 2))
    fairways_hit_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    gir_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    total_eagles: Mapped[int] = mapped_column(Integer, default=0)
    total_birdies: Mapped[int] = mapped_column(Integer, default=0)
    total_pars: Mapped[int] = mapped_column(Integer, default=0)
    total_bogeys: Mapped[int] = mapped_column(Integer, default=0)
    total_double_bogeys: Mapped[int] = mapped_column(Integer, default=0)
    total_worse: Mapped[int] = mapped_column(Integer, default=0)
    total_hole_in_ones: Mapped[int] = mapped_column(Integer, default=0)
    total_three_putts: Mapped[int] = mapped_column(Integer, default=0)
    best_score_18: Mapped[Optional[int]] = mapped_column(Integer)
    best_score_9: Mapped[Optional[int]] = mapped_column(Integer)
    best_differential: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    total_bet_won: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_bet_lost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class PlayerHoleStats(Base):
    __tablename__ = "player_hole_stats"
    __table_args__ = ({"schema": "public"},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"))
    hole_number: Mapped[int] = mapped_column(Integer, nullable=False)
    times_played: Mapped[int] = mapped_column(Integer, default=0)
    avg_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 2))
    avg_putts: Mapped[Optional[float]] = mapped_column(Numeric(4, 2))
    best_score: Mapped[Optional[int]] = mapped_column(Integer)
    worst_score: Mapped[Optional[int]] = mapped_column(Integer)
    birdies: Mapped[int] = mapped_column(Integer, default=0)
    pars: Mapped[int] = mapped_column(Integer, default=0)
    bogeys: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

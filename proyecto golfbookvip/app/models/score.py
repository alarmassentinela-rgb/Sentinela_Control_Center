import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from app.models.base import Base


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("round_id", "user_id", "hole_number"),)

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    hole_number: Mapped[int] = mapped_column(Integer, nullable=False)
    gross_score: Mapped[Optional[int]] = mapped_column(Integer)
    net_score: Mapped[Optional[int]] = mapped_column(Integer)
    putts: Mapped[Optional[int]] = mapped_column(Integer)
    played_shot: Mapped[bool] = mapped_column(Boolean, default=True)
    stableford_points: Mapped[Optional[int]] = mapped_column(Integer)
    is_birdie: Mapped[bool] = mapped_column(Boolean, default=False)
    is_eagle: Mapped[bool] = mapped_column(Boolean, default=False)
    is_albatross: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hole_in_one: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bogey: Mapped[bool] = mapped_column(Boolean, default=False)
    is_double_bogey: Mapped[bool] = mapped_column(Boolean, default=False)
    is_three_putt: Mapped[bool] = mapped_column(Boolean, default=False)
    oye_distance_cm: Mapped[Optional[int]] = mapped_column(Integer)
    oye_winner: Mapped[bool] = mapped_column(Boolean, default=False)
    shot_latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 8))
    shot_longitude: Mapped[Optional[float]] = mapped_column(Numeric(11, 8))
    notes: Mapped[Optional[str]] = mapped_column(String(500))
    entered_by: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    conflict_score: Mapped[Optional[int]] = mapped_column(Integer)
    conflict_entered_by: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    has_conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class HoleBetResult(Base):
    __tablename__ = "hole_bet_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"))
    hole_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bet_type: Mapped[Optional[str]] = mapped_column(String(30))
    winner_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id"))
    amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    is_accumulated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class RoundPlayerBalance(Base):
    __tablename__ = "round_player_balance"
    __table_args__ = (UniqueConstraint("round_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    entry_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    nassau_balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    skins_balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    birds_earned: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    three_putt_loss: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    oyes_balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    other_balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

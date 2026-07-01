import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Numeric, Text, ForeignKey, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from app.models.base import Base


class Round(Base):
    __tablename__ = "rounds"
    __table_args__ = (
        Index("idx_rounds_club", "club_id"),
        Index("idx_rounds_group", "group_id"),
        Index("idx_rounds_scheduled", "scheduled_at"),
        Index("idx_rounds_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("clubs.id", ondelete="SET NULL"))
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"))
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("courses.id"))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id"))
    name: Mapped[Optional[str]] = mapped_column(String(200))
    game_format: Mapped[str] = mapped_column(String(30), nullable=False)
    team_size: Mapped[int] = mapped_column(Integer, default=1, nullable=True)
    scoring_type: Mapped[str] = mapped_column(String(20), default="gross", nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="scheduled", nullable=True)
    holes_to_play: Mapped[int] = mapped_column(Integer, default=18, nullable=True)
    weather_temp: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))
    weather_wind: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))
    weather_conditions: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_handicap_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    max_handicap: Mapped[Optional[int]] = mapped_column(Integer)
    invite_code: Mapped[Optional[str]] = mapped_column(String(12), unique=True)
    teams_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class RoundBetConfig(Base):
    __tablename__ = "round_bet_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"), unique=True, nullable=True)
    entry_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    nassau_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    nassau_front9: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    nassau_back9: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    nassau_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    per_hole_bet: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    point_value: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    pressers_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    presser_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    birdie_prize: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    eagle_prize: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    albatross_prize: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    hole_in_one_prize: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    three_putt_penalty: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    oyes_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    oyes_prize: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    oyes_accumulates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    skins_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    skins_value: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    skins_use_net: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class RoundPlayer(Base):
    __tablename__ = "round_players"
    __table_args__ = (
        UniqueConstraint("round_id", "user_id"),
        Index(
            "uq_round_tee_group_scorer",
            "round_id",
            "tee_group",
            unique=True,
            postgresql_where=text("is_group_scorer = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    team_number: Mapped[Optional[int]] = mapped_column(Integer)
    tee_order: Mapped[Optional[int]] = mapped_column(Integer)
    match_order: Mapped[Optional[int]] = mapped_column(Integer)
    tee_group: Mapped[Optional[int]] = mapped_column(Integer)       # grupo de salida (1, 2, 3…)
    starting_hole: Mapped[Optional[int]] = mapped_column(Integer)   # hoyo donde arranca el grupo
    is_group_scorer: Mapped[bool] = mapped_column(Boolean, default=False)  # único capturista por grupo
    score_validated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))  # firma del jugador al final
    handicap_index: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))
    course_handicap: Mapped[Optional[int]] = mapped_column(Integer)
    tee_color: Mapped[Optional[str]] = mapped_column(String(10))  # black, blue, white, red
    in_bet: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="invited", nullable=True)
    participant_mode: Mapped[str] = mapped_column(String(20), default="playing", nullable=True)
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    withdrawn_reason: Mapped[Optional[str]] = mapped_column(String(200))
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class RoundTeam(Base):
    __tablename__ = "round_teams"
    __table_args__ = (UniqueConstraint("round_id", "team_number"),)

    id: Mapped[uuid.UUID] = mapped_column(
        pgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    round_id: Mapped[uuid.UUID] = mapped_column(
        pgUUID(as_uuid=True),
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class RoundSpectator(Base):
    __tablename__ = "round_spectators"
    __table_args__ = (UniqueConstraint("round_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    joined_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    left_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

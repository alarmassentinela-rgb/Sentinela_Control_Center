import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Numeric, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from app.models.base import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(20), nullable=False)
    price_monthly: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), default=0)
    price_yearly: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), default=0)
    max_members: Mapped[Optional[int]] = mapped_column(Integer)
    max_courses: Mapped[Optional[int]] = mapped_column(Integer)
    max_groups: Mapped[Optional[int]] = mapped_column(Integer)
    max_rounds_history: Mapped[Optional[int]] = mapped_column(Integer)
    features: Mapped[Optional[dict]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class PlanFeature(Base):
    __tablename__ = "plan_features"
    __table_args__ = (UniqueConstraint("plan_id", "feature_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("subscription_plans.id"))
    feature_key: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id"))
    plan_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("subscription_plans.id"))
    status: Mapped[Optional[str]] = mapped_column(String(20))
    stripe_sub_id: Mapped[Optional[str]] = mapped_column(String(200))
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    current_period_start: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class ClubSubscription(Base):
    __tablename__ = "club_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id: Mapped[Optional[uuid.UUID]] = mapped_column(pgUUID(as_uuid=True), ForeignKey("clubs.id"))
    plan_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("subscription_plans.id"))
    status: Mapped[Optional[str]] = mapped_column(String(20))
    stripe_sub_id: Mapped[Optional[str]] = mapped_column(String(200))
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    current_period_start: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

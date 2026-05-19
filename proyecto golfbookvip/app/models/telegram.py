"""Tokens efímeros para vincular cuenta de usuario con Telegram (v1.21.0)."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class TelegramLinkToken(Base):
    __tablename__ = "telegram_link_tokens"

    token: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        pgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    used_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

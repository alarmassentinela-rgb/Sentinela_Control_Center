from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date
import uuid


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    handicap_index: Optional[float] = None
    initial_handicap: Optional[float] = None
    is_verified: bool
    email_verified: bool
    is_superadmin: bool = False
    notify_email: bool = True
    notify_inapp: bool = True
    notify_telegram: bool = True
    telegram_chat_id: Optional[str] = None
    telegram_username: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    gender: Optional[str] = None
    birthdate: Optional[date] = None
    notify_email: Optional[bool] = None
    notify_inapp: Optional[bool] = None
    notify_telegram: Optional[bool] = None


class HandicapInit(BaseModel):
    initial_handicap: float  # 0.0 – 54.0 WHS máximo

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class RoundCreate(BaseModel):
    course_id: uuid.UUID
    group_id: Optional[uuid.UUID] = None
    club_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    game_format: str
    scoring_type: str = "gross"
    team_size: int = 1
    scheduled_at: datetime
    holes_to_play: int = 18
    is_handicap_valid: bool = True
    notes: Optional[str] = None


class RoundOut(BaseModel):
    id: uuid.UUID
    course_id: Optional[uuid.UUID] = None
    group_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    game_format: str
    scoring_type: str
    status: str
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    holes_to_play: int
    team_size: int = 1
    is_handicap_valid: bool
    invite_code: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RoundUpdate(BaseModel):
    name: Optional[str] = None
    course_id: Optional[uuid.UUID] = None
    game_format: Optional[str] = None
    team_size: Optional[int] = None
    holes_to_play: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    is_handicap_valid: Optional[bool] = None
    notes: Optional[str] = None


class BetConfigCreate(BaseModel):
    entry_fee: float = 0
    nassau_enabled: bool = False
    nassau_front9: float = 0
    nassau_back9: float = 0
    nassau_total: float = 0
    per_hole_bet: float = 0
    point_value: float = 0
    birdie_prize: float = 0
    eagle_prize: float = 0
    hole_in_one_prize: float = 0
    three_putt_penalty: float = 0
    oyes_enabled: bool = False
    oyes_prize: float = 0
    oyes_accumulates: bool = True
    skins_enabled: bool = False
    skins_value: float = 0
    skins_use_net: bool = False

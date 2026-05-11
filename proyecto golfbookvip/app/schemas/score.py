from pydantic import BaseModel, model_validator
from typing import Optional
import uuid


class ScoreSubmit(BaseModel):
    hole_number: int
    gross_score: int
    putts: Optional[int] = None
    played_shot: bool = True
    oye_distance_cm: Optional[int] = None
    shot_latitude: Optional[float] = None
    shot_longitude: Optional[float] = None
    notes: Optional[str] = None
    for_user_id: Optional[uuid.UUID] = None   # captura para compañero del mismo grupo

    @model_validator(mode="after")
    def validate_hole(self) -> "ScoreSubmit":
        if not 1 <= self.hole_number <= 18:
            raise ValueError("hole_number debe estar entre 1 y 18")
        if self.gross_score < 1:
            raise ValueError("gross_score inválido")
        return self


class ScoreOut(BaseModel):
    id: uuid.UUID
    round_id: uuid.UUID
    user_id: uuid.UUID
    hole_number: int
    gross_score: Optional[int] = None
    net_score: Optional[int] = None
    putts: Optional[int] = None
    stableford_points: Optional[int] = None
    is_birdie: bool
    is_eagle: bool
    is_albatross: bool
    is_hole_in_one: bool
    is_bogey: bool
    is_double_bogey: bool
    is_three_putt: bool
    oye_winner: bool
    has_conflict: bool = False
    conflict_score: Optional[int] = None

    model_config = {"from_attributes": True}

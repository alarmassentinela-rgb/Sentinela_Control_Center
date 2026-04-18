"""
Motor de scoring: calcula banderas especiales y puntos Stableford
a partir del gross_score y el par del hoyo.
"""
from typing import Optional
from app.schemas.score import ScoreSubmit
from app.models.score import Score


def calculate_score_flags(
    gross: int,
    par: int,
    course_handicap: int,
    stroke_index: int,
    putts: Optional[int],
) -> dict:
    """
    Calcula todos los flags del score para un hoyo.
    """
    relative = gross - par
    strokes = 1 if stroke_index <= course_handicap else 0
    net = gross - strokes

    flags = {
        "net_score": net,
        "is_hole_in_one": gross == 1,
        "is_albatross": relative == -3,
        "is_eagle": relative == -2,
        "is_birdie": relative == -1,
        "is_bogey": relative == 1,
        "is_double_bogey": relative == 2,
        "is_three_putt": putts is not None and putts >= 3,
    }
    return flags


def calculate_stableford(
    gross: int,
    par: int,
    course_handicap: int,
    stroke_index: int,
    modified: bool = False,
) -> int:
    """
    Stableford estándar: 2 = par, +1 por cada golpe bajo par, -1 por sobre par.
    Stableford modificado: mínimo 0 puntos (no se penaliza doble bogey+).
    """
    strokes = 1 if stroke_index <= course_handicap else 0
    net_relative = gross - strokes - par

    points = 2 - net_relative
    if modified:
        points = max(0, points)
    return points


def apply_score_to_model(
    score: Score,
    data: ScoreSubmit,
    par: int,
    stroke_index: int,
    course_handicap: int,
    game_format: str,
) -> None:
    """
    Aplica los datos calculados al modelo Score en memoria (sin commit).
    """
    score.gross_score = data.gross_score
    score.putts = data.putts
    score.played_shot = data.played_shot
    score.oye_distance_cm = data.oye_distance_cm
    score.shot_latitude = data.shot_latitude
    score.shot_longitude = data.shot_longitude
    score.notes = data.notes

    flags = calculate_score_flags(
        data.gross_score, par, course_handicap, stroke_index, data.putts
    )
    score.net_score = flags["net_score"]
    score.is_hole_in_one = flags["is_hole_in_one"]
    score.is_albatross = flags["is_albatross"]
    score.is_eagle = flags["is_eagle"]
    score.is_birdie = flags["is_birdie"]
    score.is_bogey = flags["is_bogey"]
    score.is_double_bogey = flags["is_double_bogey"]
    score.is_three_putt = flags["is_three_putt"]

    if game_format in ("stableford", "stableford_modified"):
        modified = game_format == "stableford_modified"
        score.stableford_points = calculate_stableford(
            data.gross_score, par, course_handicap, stroke_index, modified
        )

"""
Motor de scoring: calcula banderas especiales y puntos Stableford
a partir del gross_score y el par del hoyo.
"""
from typing import Optional
from app.schemas.score import ScoreSubmit
from app.models.score import Score


def effective_handicap(course_handicap: int, max_handicap: Optional[int]) -> int:
    """Aplica el tope de handicap configurado en la ronda.

    max_handicap None/0 = sin tope. Cuando hay tope, el CH efectivo = min(CH real, tope).
    """
    if course_handicap is None:
        return 0
    ch = max(0, course_handicap)
    if max_handicap is None or max_handicap <= 0:
        return ch
    return min(ch, max_handicap)


def strokes_received(course_handicap: int, stroke_index: int) -> int:
    """Fórmula WHS estándar: strokes recibidos en un hoyo dado el CH y SI del hoyo.

    Para CH ≤ 18: 1 stroke en los CH hoyos con SI más bajo (los más difíciles), 0 en el resto.
    Para CH > 18: base = CH//18 strokes en TODOS los hoyos, + 1 extra en los (CH%18) más
                  difíciles. Ej. CH=22 → 1 stroke por hoyo + 1 extra en SI 1-4 = 2 en SI 1-4.

    Maneja correctamente CH desde 0 hasta cualquier valor (54+ típico para principiantes WHS).
    """
    if course_handicap is None or stroke_index is None:
        return 0
    if stroke_index < 1 or stroke_index > 18:
        return 0
    ch = max(0, course_handicap)
    base = ch // 18
    extra = 1 if (ch % 18) >= stroke_index else 0
    return base + extra


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
    strokes = strokes_received(course_handicap, stroke_index)
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
    strokes = strokes_received(course_handicap, stroke_index)
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
    max_handicap: Optional[int] = None,
) -> None:
    """
    Aplica los datos calculados al modelo Score en memoria (sin commit).
    Si la ronda tiene max_handicap, el CH del jugador se topa a ese valor antes
    de calcular strokes (afecta net_score y stableford_points).
    """
    eff_ch = effective_handicap(course_handicap, max_handicap)

    score.gross_score = data.gross_score
    score.putts = data.putts
    score.played_shot = data.played_shot
    score.oye_distance_cm = data.oye_distance_cm
    score.shot_latitude = data.shot_latitude
    score.shot_longitude = data.shot_longitude
    score.notes = data.notes

    flags = calculate_score_flags(
        data.gross_score, par, eff_ch, stroke_index, data.putts
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
            data.gross_score, par, eff_ch, stroke_index, modified
        )

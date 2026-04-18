"""
Motor de cálculo de Hándicap WHS (World Handicap System)
Referencia: https://www.usga.org/content/usga/home-page/handicapping/roh/Content/rules/5%201%20Procedure%20for%20Calculating%20a%20Handicap%20Index.htm
"""
from datetime import date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.handicap import ScoreDifferential, HandicapHistory
from app.models.user import User


def calculate_differential(
    adjusted_gross_score: int,
    course_rating: float,
    slope_rating: int,
    pcc: float = 0,
) -> float:
    """
    Fórmula WHS: (AGS - CR - PCC) × (113 / SR)
    """
    return round((adjusted_gross_score - course_rating - pcc) * (113 / slope_rating), 1)


def apply_score_adjustment(gross_score: int, par: int, hole_handicap: int, course_handicap: int) -> int:
    """
    Net Double Bogey: máximo permitido por hoyo para el hándicap.
    Net Double Bogey = par + 2 + strokes received on hole
    """
    strokes_on_hole = 1 if hole_handicap <= course_handicap else 0
    max_score = par + 2 + strokes_on_hole
    return min(gross_score, max_score)


def select_differentials(differentials: list[float]) -> list[float]:
    """
    WHS: de los últimos 20 diferenciales, selecciona los mejores N según tabla:
    ≥20 rondas → mejores 8; 19 → mejores 7; ... ver tabla oficial.
    """
    count = len(differentials)
    if count < 3:
        return []
    table = {
        3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 3, 10: 3,
        11: 3, 12: 4, 13: 4, 14: 4, 15: 5, 16: 5, 17: 6,
        18: 6, 19: 7, 20: 8,
    }
    n = table.get(min(count, 20), 8)
    return sorted(differentials)[:n]


def apply_caps(new_index: float, low_index: float) -> tuple[float, bool, bool]:
    """
    Soft cap: si el índice sube más de 3.0 sobre el low, el exceso se reduce al 50%.
    Hard cap: el índice no puede superar low_index + 5.0.
    Retorna (index_ajustado, soft_applied, hard_applied)
    """
    soft_applied = hard_applied = False
    if new_index > low_index + 3.0:
        soft_applied = True
        excess = new_index - (low_index + 3.0)
        new_index = low_index + 3.0 + (excess * 0.5)
    if new_index > low_index + 5.0:
        hard_applied = True
        new_index = low_index + 5.0
    return round(new_index, 1), soft_applied, hard_applied


async def recalculate_handicap(user_id: str, db: AsyncSession) -> Optional[float]:
    """
    Recalcula el Handicap Index del usuario y persiste el resultado.
    Retorna el nuevo índice, o None si no hay suficientes rondas.
    """
    result = await db.execute(
        select(ScoreDifferential)
        .where(ScoreDifferential.user_id == user_id, ScoreDifferential.is_counting == True)
        .order_by(desc(ScoreDifferential.played_at))
        .limit(20)
    )
    diffs_rows = result.scalars().all()

    if len(diffs_rows) < 3:
        return None

    differentials = [float(d.differential) for d in diffs_rows]
    selected = select_differentials(differentials)
    if not selected:
        return None

    raw_index = round(sum(selected) / len(selected) - 0.0, 1)

    # Low handicap index (mínimo histórico de los últimos 12 meses)
    result2 = await db.execute(
        select(HandicapHistory.handicap_index)
        .where(HandicapHistory.user_id == user_id)
        .order_by(desc(HandicapHistory.calculation_date))
        .limit(24)
    )
    history = result2.scalars().all()
    low_index = min([float(h) for h in history], default=raw_index)

    final_index, soft_cap, hard_cap = apply_caps(raw_index, low_index)

    # Guardar historial
    prev_result = await db.execute(
        select(HandicapHistory)
        .where(HandicapHistory.user_id == user_id)
        .order_by(desc(HandicapHistory.calculation_date))
        .limit(1)
    )
    prev = prev_result.scalar_one_or_none()
    prev_index = float(prev.handicap_index) if prev else None

    record = HandicapHistory(
        user_id=user_id,
        handicap_index=final_index,
        previous_index=prev_index,
        differentials_used={"values": selected},
        calculation_date=date.today(),
        rounds_counted=len(selected),
        soft_cap_applied=soft_cap,
        hard_cap_applied=hard_cap,
    )
    db.add(record)

    # Actualizar usuario
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        from datetime import datetime, timezone
        user.handicap_index = final_index
        user.handicap_last_updated = datetime.now(timezone.utc)
        user.handicap_rounds_count = len(diffs_rows)

    await db.flush()
    return final_index


def calculate_course_handicap(handicap_index: float, slope_rating: int, course_rating: float, par: int) -> int:
    """
    Course Handicap = HI × (SR / 113) + (CR - Par)
    """
    return round(handicap_index * (slope_rating / 113) + (course_rating - par))

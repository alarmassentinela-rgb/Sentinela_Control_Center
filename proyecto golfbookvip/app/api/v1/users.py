import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, or_

from app.core.deps import CurrentUser, DB
from app.models.user import User
from app.models.handicap import PlayerStats, HandicapHistory
from app.models.group import UserFollow
from app.schemas.user import UserOut, UserUpdate, HandicapInit

router = APIRouter()


class LookupBatchPayload(BaseModel):
    emails: list[str] = Field(..., min_length=1, max_length=500)


@router.post("/lookup-batch")
async def lookup_users_batch(payload: LookupBatchPayload, current_user: CurrentUser, db: DB):
    """Resuelve una lista de emails contra users. Auth required. Útil para preview
    de import CSV antes de crear el club (no necesita club_id). v1.19.0."""
    # Normalizar emails
    normalized: list[str] = []
    seen: set[str] = set()
    for e in payload.emails:
        e_norm = (e or "").strip().lower()
        if not e_norm or "@" not in e_norm or e_norm in seen:
            continue
        seen.add(e_norm)
        normalized.append(e_norm)
    if not normalized:
        return {"matches": [], "not_found": []}
    res = await db.execute(select(User).where(User.email.in_(normalized)))
    found_by_email: dict[str, User] = {u.email.lower(): u for u in res.scalars().all()}
    matches = []
    not_found = []
    for e in normalized:
        u = found_by_email.get(e)
        if u:
            matches.append({
                "email": e,
                "user_id": str(u.id),
                "first_name": u.first_name,
                "last_name": u.last_name,
                "username": u.username,
            })
        else:
            not_found.append(e)
    return {"matches": matches, "not_found": not_found}


@router.get("/me", response_model=UserOut)
async def get_me(current_user: CurrentUser):
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_me(data: UserUpdate, current_user: CurrentUser, db: DB):
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    db.add(current_user)
    return current_user


@router.post("/me/handicap-init", response_model=UserOut)
async def set_initial_handicap(data: HandicapInit, current_user: CurrentUser, db: DB):
    if current_user.initial_handicap is not None:
        raise HTTPException(status_code=400, detail="El hándicap inicial ya fue registrado")
    if not (0.0 <= data.initial_handicap <= 54.0):
        raise HTTPException(status_code=422, detail="El hándicap debe estar entre 0.0 y 54.0")
    current_user.initial_handicap = data.initial_handicap
    current_user.handicap_index = data.initial_handicap
    from datetime import datetime, timezone
    current_user.handicap_last_updated = datetime.now(timezone.utc)
    db.add(current_user)
    return current_user


@router.get("/me/stats")
async def get_my_stats(current_user: CurrentUser, db: DB):
    """Estadísticas calculadas on-demand desde los scores capturados.

    Itera rondas finished donde participó el usuario y agrega:
    - Conteo de rondas / hoyos
    - Promedio gross y putts
    - Conteos por categoría (birdies/eagles/pars/bogeys/etc.)
    - Mejor 18 y mejor 9
    - Mejor diferencial de hándicap
    - Total ganado/perdido en apuestas (de balances persistidos)
    """
    from app.models.round import Round, RoundPlayer
    from app.models.score import Score, RoundPlayerBalance
    from app.models.course import CourseHole
    from app.models.handicap import ScoreDifferential

    # Rondas finalizadas donde participó como playing
    rounds_q = await db.execute(
        select(Round, RoundPlayer)
        .join(RoundPlayer, RoundPlayer.round_id == Round.id)
        .where(
            RoundPlayer.user_id == current_user.id,
            Round.status == "finished",
            RoundPlayer.participant_mode == "playing",
            RoundPlayer.withdrawn_at.is_(None),
        )
    )
    rounds_rows = rounds_q.all()
    total_rounds = len(rounds_rows)

    total_holes = 0
    total_gross = 0
    total_putts = 0
    holes_with_putts = 0
    total_eagles = total_birdies = total_pars = total_bogeys = 0
    total_double_bogeys = total_worse = total_hio = total_three_putts = 0
    best_score_18: int | None = None
    best_score_9: int | None = None

    for round_, _rp in rounds_rows:
        # Scores del usuario en esa ronda
        scores_q = await db.execute(
            select(Score).where(
                Score.round_id == round_.id,
                Score.user_id == current_user.id,
            )
        )
        scores = scores_q.scalars().all()
        if not scores:
            continue

        # Pars del campo (mapa hole_number → par)
        holes_q = await db.execute(
            select(CourseHole).where(CourseHole.course_id == round_.course_id)
        )
        par_by_hole = {h.hole_number: (h.par or 0) for h in holes_q.scalars().all()}

        round_gross = 0
        round_holes_with_score = 0
        for s in scores:
            if not s.gross_score:
                continue
            round_gross += s.gross_score
            round_holes_with_score += 1
            par = par_by_hole.get(s.hole_number, 0)
            if s.putts is not None:
                total_putts += s.putts
                holes_with_putts += 1
            if s.is_hole_in_one:
                total_hio += 1
            if s.is_three_putt:
                total_three_putts += 1
            # Clasificar score vs par
            if s.is_albatross or (par and s.gross_score == par - 3):
                total_eagles += 1  # se agrupa con eagles para el conteo "águilas+"
            elif s.is_eagle or (par and s.gross_score == par - 2):
                total_eagles += 1
            elif s.is_birdie or (par and s.gross_score == par - 1):
                total_birdies += 1
            elif par and s.gross_score == par:
                total_pars += 1
            elif s.is_bogey or (par and s.gross_score == par + 1):
                total_bogeys += 1
            elif s.is_double_bogey or (par and s.gross_score == par + 2):
                total_double_bogeys += 1
            else:
                total_worse += 1

        total_holes += round_holes_with_score
        total_gross += round_gross

        # Mejor 18 / 9
        if round_holes_with_score == round_.holes_to_play and round_gross > 0:
            if round_.holes_to_play == 18:
                if best_score_18 is None or round_gross < best_score_18:
                    best_score_18 = round_gross
            elif round_.holes_to_play == 9:
                if best_score_9 is None or round_gross < best_score_9:
                    best_score_9 = round_gross

    avg_score = (total_gross / total_holes) if total_holes > 0 else None
    avg_putts_per_hole = (total_putts / holes_with_putts) if holes_with_putts > 0 else None
    avg_putts_per_round = (total_putts / total_rounds) if total_rounds > 0 else None

    # Mejor diferencial de hándicap
    diff_q = await db.execute(
        select(ScoreDifferential.differential)
        .where(ScoreDifferential.user_id == current_user.id)
        .order_by(ScoreDifferential.differential.asc())
        .limit(1)
    )
    best_diff = diff_q.scalar_one_or_none()

    # Total ganado/perdido en apuestas (desde balances persistidos)
    bal_q = await db.execute(
        select(RoundPlayerBalance.total_balance).where(RoundPlayerBalance.user_id == current_user.id)
    )
    totals = [float(t) for (t,) in bal_q.all() if t is not None]
    total_bet_won = sum(t for t in totals if t > 0)
    total_bet_lost = abs(sum(t for t in totals if t < 0))

    return {
        "total_rounds": total_rounds,
        "total_holes": total_holes,
        "avg_score": round(avg_score, 2) if avg_score is not None else None,
        "avg_putts_per_round": round(avg_putts_per_round, 2) if avg_putts_per_round is not None else None,
        "avg_putts_per_hole": round(avg_putts_per_hole, 2) if avg_putts_per_hole is not None else None,
        "fairways_hit_pct": None,  # No se trackea en Score actualmente
        "gir_pct": None,            # No se trackea en Score actualmente
        "total_eagles": total_eagles,
        "total_birdies": total_birdies,
        "total_pars": total_pars,
        "total_bogeys": total_bogeys,
        "total_double_bogeys": total_double_bogeys,
        "total_worse": total_worse,
        "total_hole_in_ones": total_hio,
        "total_three_putts": total_three_putts,
        "best_score_18": best_score_18,
        "best_score_9": best_score_9,
        "best_differential": float(best_diff) if best_diff is not None else None,
        "total_bet_won": total_bet_won,
        "total_bet_lost": total_bet_lost,
    }


@router.get("/me/handicap-history")
async def get_handicap_history(current_user: CurrentUser, db: DB):
    from sqlalchemy import desc
    result = await db.execute(
        select(HandicapHistory)
        .where(HandicapHistory.user_id == current_user.id)
        .order_by(desc(HandicapHistory.calculation_date))
        .limit(20)
    )
    history = result.scalars().all()
    return [
        {
            "handicap_index": float(h.handicap_index),
            "previous_index": float(h.previous_index) if h.previous_index else None,
            "calculation_date": h.calculation_date.isoformat(),
            "rounds_counted": h.rounds_counted,
            "soft_cap_applied": h.soft_cap_applied,
            "hard_cap_applied": h.hard_cap_applied,
        }
        for h in history
    ]


@router.get("/me/following")
async def get_following(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(UserFollow, User)
        .join(User, UserFollow.following_id == User.id)
        .where(UserFollow.follower_id == current_user.id, UserFollow.status == 'active')
        .order_by(User.first_name)
    )
    rows = result.all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "handicap_index": float(u.handicap_index) if u.handicap_index else None,
        }
        for _, u in rows
    ]


@router.get("/me/round-history")
async def get_round_history(current_user: CurrentUser, db: DB):
    """Per-round stats for the last 20 finished rounds."""
    from app.models.round import Round, RoundPlayer
    from app.models.score import Score
    from app.models.handicap import ScoreDifferential
    from app.models.course import Course
    from sqlalchemy import desc

    # Finished rounds where I played
    rp_res = await db.execute(
        select(Round, Course)
        .join(RoundPlayer, RoundPlayer.round_id == Round.id)
        .outerjoin(Course, Course.id == Round.course_id)
        .where(
            RoundPlayer.user_id == current_user.id,
            Round.status == 'finished',
        )
        .order_by(desc(Round.finished_at))
        .limit(20)
    )
    round_rows = rp_res.all()
    if not round_rows:
        return []

    result = []
    for round_, course in round_rows:
        from app.models.course import CourseHole
        scores_res = await db.execute(
            select(Score, CourseHole.par)
            .outerjoin(
                CourseHole,
                (CourseHole.course_id == round_.course_id) &
                (CourseHole.hole_number == Score.hole_number)
            )
            .where(Score.round_id == round_.id, Score.user_id == current_user.id)
        )
        score_rows = scores_res.all()
        scores = [r[0] for r in score_rows]
        pars_map = {r[0].hole_number: r[1] for r in score_rows}  # hole_number -> par

        total_gross = sum(s.gross_score or 0 for s in scores)
        total_net   = sum(s.net_score   or 0 for s in scores)
        total_putts = sum(s.putts       or 0 for s in scores)
        birdies     = sum(1 for s in scores if s.is_birdie)
        eagles      = sum(1 for s in scores if s.is_eagle or s.is_albatross or s.is_hole_in_one)
        pars        = sum(1 for s in scores if s.gross_score and pars_map.get(s.hole_number) and s.gross_score == pars_map[s.hole_number])
        bogeys      = sum(1 for s in scores if s.is_bogey)
        doubles     = sum(1 for s in scores if s.is_double_bogey)
        three_putts = sum(1 for s in scores if s.is_three_putt)

        diff_res = await db.scalar(
            select(ScoreDifferential.differential)
            .where(ScoreDifferential.round_id == round_.id, ScoreDifferential.user_id == current_user.id)
        )

        result.append({
            "round_id":    str(round_.id),
            "name":        round_.name,
            "course_name": course.name if course else None,
            "game_format": round_.game_format,
            "holes_to_play": round_.holes_to_play,
            "played_at":   (round_.finished_at or round_.scheduled_at).date().isoformat(),
            "holes_played": len(scores),
            "total_gross": total_gross,
            "total_net":   total_net,
            "total_putts": total_putts,
            "birdies":     birdies,
            "eagles":      eagles,
            "bogeys":      bogeys,
            "doubles":     doubles,
            "three_putts": three_putts,
            "differential": float(diff_res) if diff_res else None,
        })
    return result


# ─── Historial financiero (balance de apuestas por ronda) ─────────────────────

@router.get("/me/balance-history")
async def get_balance_history(
    current_user: CurrentUser,
    db: DB,
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(200, ge=1, le=1000),
):
    """Lista de rondas finalizadas donde participó el usuario, con su balance final.

    Usa los balances persistidos en `round_player_balance` (escritos al cierre de
    la ronda). Si una ronda no tiene balance persistido (legacy), se calcula on-demand
    y se guarda (lazy backfill). Solo rondas con bets activas y total != 0.
    """
    from datetime import datetime, date as date_type
    from app.models.round import Round, RoundPlayer
    from app.models.course import Course
    from app.models.score import RoundPlayerBalance
    from app.services import balances as balances_svc

    # Parse dates
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=422, detail="start_date inválido (YYYY-MM-DD)")
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            # Incluye todo el día final
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=422, detail="end_date inválido (YYYY-MM-DD)")

    # Buscar todas las rondas finalizadas donde el usuario participó
    rounds_query = (
        select(Round, RoundPlayer, Course)
        .join(RoundPlayer, RoundPlayer.round_id == Round.id)
        .outerjoin(Course, Course.id == Round.course_id)
        .where(
            RoundPlayer.user_id == current_user.id,
            Round.status == "finished",
            RoundPlayer.participant_mode == "playing",
            RoundPlayer.withdrawn_at.is_(None),
        )
        .order_by(Round.finished_at.desc())
    )
    if start_dt:
        rounds_query = rounds_query.where(Round.finished_at >= start_dt)
    if end_dt:
        rounds_query = rounds_query.where(Round.finished_at <= end_dt)
    rounds_query = rounds_query.limit(limit)

    rows = (await db.execute(rounds_query)).all()

    items = []
    for round_, rp, course in rows:
        # Buscar balance persistido
        bal_res = await db.execute(
            select(RoundPlayerBalance).where(
                RoundPlayerBalance.round_id == round_.id,
                RoundPlayerBalance.user_id == current_user.id,
            )
        )
        bal = bal_res.scalar_one_or_none()

        # Detectar si el balance está obsoleto:
        # - No existe (legacy)
        # - El row es un placeholder creado al invitar (updated_at < finished_at)
        needs_recompute = (
            bal is None
            or (round_.finished_at and bal.updated_at and bal.updated_at < round_.finished_at)
        )

        # Lazy backfill: recalcular y persistir balances finales
        if needs_recompute:
            try:
                await balances_svc.persist_balances(str(round_.id), db)
                bal_res = await db.execute(
                    select(RoundPlayerBalance).where(
                        RoundPlayerBalance.round_id == round_.id,
                        RoundPlayerBalance.user_id == current_user.id,
                    )
                )
                bal = bal_res.scalar_one_or_none()
            except Exception as ex:
                import logging
                logging.warning(f"lazy persist_balances failed for round {round_.id}: {ex}")

        if not bal:
            continue
        # Skip si el jugador no tuvo movimiento (todo $0 en todas las categorías)
        all_zero = (
            abs(float(bal.entry_fee or 0)) < 0.01
            and abs(float(bal.nassau_balance or 0)) < 0.01
            and abs(float(bal.other_balance or 0)) < 0.01
            and abs(float(bal.birds_earned or 0)) < 0.01
            and abs(float(bal.three_putt_loss or 0)) < 0.01
            and abs(float(bal.skins_balance or 0)) < 0.01
            and abs(float(bal.oyes_balance or 0)) < 0.01
            and abs(float(bal.total_balance or 0)) < 0.01
        )
        if all_zero:
            continue

        items.append({
            "round_id": str(round_.id),
            "round_name": round_.name,
            "course_name": course.name if course else None,
            "course_city": course.city if course else None,
            "game_format": round_.game_format,
            "scheduled_at": round_.scheduled_at.isoformat(),
            "finished_at": round_.finished_at.isoformat() if round_.finished_at else None,
            "breakdown": {
                "entry_fee": float(bal.entry_fee or 0),
                "nassau": float(bal.nassau_balance or 0),
                "per_hole": float(bal.other_balance or 0),
                "prizes": float(bal.birds_earned or 0),
                "penalties": float(bal.three_putt_loss or 0),
                "skins": float(bal.skins_balance or 0),
                "oyes": float(bal.oyes_balance or 0),
                "total": float(bal.total_balance or 0),
            },
        })

    return {"items": items, "count": len(items)}


@router.get("/me/balance-summary")
async def get_balance_summary(
    current_user: CurrentUser,
    db: DB,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Resumen agregado + datos para gráfica mensual del historial financiero del usuario.

    Llama a /me/balance-history internamente para consistencia. Útil para dashboards
    y el resumen del estado de cuenta.
    """
    history = await get_balance_history(current_user=current_user, db=db,
                                         start_date=start_date, end_date=end_date, limit=1000)
    items = history["items"]

    # Agregaciones
    rounds_played = len(items)
    rounds_won = sum(1 for it in items if it["breakdown"]["total"] > 0.01)
    rounds_lost = sum(1 for it in items if it["breakdown"]["total"] < -0.01)
    rounds_tied = rounds_played - rounds_won - rounds_lost
    net_balance = sum(it["breakdown"]["total"] for it in items)
    total_won = sum(it["breakdown"]["total"] for it in items if it["breakdown"]["total"] > 0)
    total_paid = sum(it["breakdown"]["total"] for it in items if it["breakdown"]["total"] < 0)

    biggest_win = None
    biggest_loss = None
    if items:
        sorted_by_total = sorted(items, key=lambda x: x["breakdown"]["total"], reverse=True)
        top = sorted_by_total[0]
        bot = sorted_by_total[-1]
        if top["breakdown"]["total"] > 0:
            biggest_win = {
                "round_id": top["round_id"],
                "round_name": top["round_name"],
                "amount": top["breakdown"]["total"],
                "date": top["finished_at"],
            }
        if bot["breakdown"]["total"] < 0:
            biggest_loss = {
                "round_id": bot["round_id"],
                "round_name": bot["round_name"],
                "amount": bot["breakdown"]["total"],
                "date": bot["finished_at"],
            }

    # Agregación por mes para gráfica
    from collections import defaultdict
    month_totals: dict[str, float] = defaultdict(float)
    for it in items:
        if it.get("finished_at"):
            month_key = it["finished_at"][:7]  # YYYY-MM
            month_totals[month_key] += it["breakdown"]["total"]
    chart_monthly = sorted(
        [{"month": k, "total": round(v, 2)} for k, v in month_totals.items()],
        key=lambda x: x["month"],
    )

    # Agregación por tipo de apuesta (cuánto se ganó/perdió neto en cada categoría)
    by_bet_type = {
        "entry_fee": sum(it["breakdown"]["entry_fee"] for it in items),
        "nassau": sum(it["breakdown"]["nassau"] for it in items),
        "per_hole": sum(it["breakdown"]["per_hole"] for it in items),
        "prizes": sum(it["breakdown"]["prizes"] for it in items),
        "penalties": sum(it["breakdown"]["penalties"] for it in items),
        "skins": sum(it["breakdown"]["skins"] for it in items),
        "oyes": sum(it["breakdown"]["oyes"] for it in items),
    }

    return {
        "rounds_played": rounds_played,
        "rounds_won": rounds_won,
        "rounds_lost": rounds_lost,
        "rounds_tied": rounds_tied,
        "net_balance": net_balance,
        "total_won": total_won,
        "total_paid": total_paid,
        "biggest_win": biggest_win,
        "biggest_loss": biggest_loss,
        "chart_monthly": chart_monthly,
        "by_bet_type": by_bet_type,
    }


@router.get("/me/feed")
async def get_feed(current_user: CurrentUser, db: DB):
    from app.models.round import Round, RoundPlayer
    from app.models.course import Course

    # Users I follow
    following_res = await db.execute(
        select(UserFollow.following_id).where(
            UserFollow.follower_id == current_user.id,
            UserFollow.status == 'active'
        )
    )
    following_ids = [r[0] for r in following_res.all()]
    if not following_ids:
        return []

    # Distinct rounds where they played (not just invited)
    rp_res = await db.execute(
        select(RoundPlayer.round_id).distinct().where(
            RoundPlayer.user_id.in_(following_ids),
            RoundPlayer.status != 'invited'
        )
    )
    round_ids = [r[0] for r in rp_res.all()]
    if not round_ids:
        return []

    # Rounds (active or finished), newest first
    rounds_res = await db.execute(
        select(Round, Course)
        .outerjoin(Course, Round.course_id == Course.id)
        .where(
            Round.id.in_(round_ids),
            Round.status.in_(['active', 'finished'])
        )
        .order_by(Round.scheduled_at.desc())
        .limit(30)
    )
    round_rows = rounds_res.all()
    if not round_rows:
        return []

    feed = []
    for r, course in round_rows:
        players_res = await db.execute(
            select(RoundPlayer, User)
            .join(User, RoundPlayer.user_id == User.id)
            .where(
                RoundPlayer.round_id == r.id,
                RoundPlayer.user_id.in_(following_ids),
                RoundPlayer.status != 'invited'
            )
        )
        players = players_res.all()
        feed.append({
            "round_id": str(r.id),
            "name": r.name,
            "course_name": course.name if course else None,
            "game_format": r.game_format,
            "status": r.status,
            "holes_to_play": r.holes_to_play,
            "scheduled_at": r.scheduled_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "players": [
                {
                    "user_id": str(u.id),
                    "username": u.username,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "handicap_index": float(u.handicap_index) if u.handicap_index else None,
                    "tee_color": rp.tee_color,
                }
                for rp, u in players
            ],
        })
    return feed


@router.get("/search")
async def search_users(q: str, current_user: CurrentUser, db: DB):
    pattern = f"%{q}%"
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.id != current_user.id,
            or_(
                User.username.ilike(pattern),
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
            )
        ).limit(20)
    )
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "handicap_index": float(u.handicap_index) if u.handicap_index else None,
        }
        for u in users
    ]


@router.post("/{user_id}/follow", status_code=201)
async def follow_user(user_id: uuid.UUID, current_user: CurrentUser, db: DB):
    if user_id == current_user.id:
        raise HTTPException(400, "No puedes seguirte a ti mismo")
    target = await db.scalar(select(User).where(User.id == user_id, User.is_active == True))
    if not target:
        raise HTTPException(404, "Usuario no encontrado")
    existing = await db.scalar(
        select(UserFollow).where(UserFollow.follower_id == current_user.id, UserFollow.following_id == user_id)
    )
    if existing:
        if existing.status == 'active':
            raise HTTPException(400, "Ya sigues a este usuario")
        existing.status = 'active'
        db.add(existing)
    else:
        db.add(UserFollow(follower_id=current_user.id, following_id=user_id, status='active'))
    return {"status": "following"}


@router.delete("/{user_id}/follow", status_code=204)
async def unfollow_user(user_id: uuid.UUID, current_user: CurrentUser, db: DB):
    existing = await db.scalar(
        select(UserFollow).where(
            UserFollow.follower_id == current_user.id,
            UserFollow.following_id == user_id,
            UserFollow.status == 'active'
        )
    )
    if not existing:
        raise HTTPException(404, "No sigues a este usuario")
    existing.status = 'inactive'
    db.add(existing)


@router.get("/{username}", response_model=UserOut)
async def get_user_profile(username: str, db: DB):
    result = await db.execute(
        select(User).where(User.username == username, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

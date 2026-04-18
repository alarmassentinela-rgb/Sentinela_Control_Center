import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, or_

from app.core.deps import CurrentUser, DB
from app.models.user import User
from app.models.handicap import PlayerStats, HandicapHistory
from app.models.group import UserFollow
from app.schemas.user import UserOut, UserUpdate, HandicapInit

router = APIRouter()


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
    result = await db.execute(
        select(PlayerStats).where(PlayerStats.user_id == current_user.id)
    )
    stats = result.scalar_one_or_none()
    if not stats:
        raise HTTPException(status_code=404, detail="Stats no encontradas")
    return {
        "total_rounds": stats.total_rounds,
        "total_holes": stats.total_holes,
        "avg_score": float(stats.avg_score) if stats.avg_score else None,
        "avg_putts_per_round": float(stats.avg_putts_per_round) if stats.avg_putts_per_round else None,
        "avg_putts_per_hole": float(stats.avg_putts_per_hole) if stats.avg_putts_per_hole else None,
        "fairways_hit_pct": float(stats.fairways_hit_pct) if stats.fairways_hit_pct else None,
        "gir_pct": float(stats.gir_pct) if stats.gir_pct else None,
        "total_eagles": stats.total_eagles,
        "total_birdies": stats.total_birdies,
        "total_pars": stats.total_pars,
        "total_bogeys": stats.total_bogeys,
        "total_double_bogeys": stats.total_double_bogeys,
        "total_worse": stats.total_worse,
        "total_hole_in_ones": stats.total_hole_in_ones,
        "total_three_putts": stats.total_three_putts,
        "best_score_18": stats.best_score_18,
        "best_score_9": stats.best_score_9,
        "best_differential": float(stats.best_differential) if stats.best_differential else None,
        "total_bet_won": float(stats.total_bet_won),
        "total_bet_lost": float(stats.total_bet_lost),
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

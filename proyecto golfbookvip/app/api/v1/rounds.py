from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, delete, func, update
from typing import Optional
import uuid, secrets, string
from datetime import date as date_type

from app.core.deps import CurrentUser, DB
from app.models.round import Round, RoundPlayer, RoundBetConfig
from app.models.course import Course, CourseHole
from app.models.score import Score, RoundPlayerBalance
from app.models.handicap import ScoreDifferential
from app.models.user import User
from app.models.group import GroupMember
from app.schemas.round import RoundCreate, RoundOut, BetConfigCreate, RoundUpdate
from app.schemas.score import ScoreSubmit, ScoreOut
from app.services import scoring as scoring_svc
from app.services import handicap as hcp_svc
from app.services import balances as balances_svc
from app.services.ws_manager import manager
from app.services.notifications import push as notify

router = APIRouter()


@router.get("")
async def list_my_rounds(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Round, Course)
        .join(RoundPlayer, RoundPlayer.round_id == Round.id)
        .outerjoin(Course, Course.id == Round.course_id)
        .where(RoundPlayer.user_id == current_user.id)
        .order_by(Round.scheduled_at.desc())
        .limit(50)
    )
    rows = result.all()
    out = []
    for round_, course in rows:
        # Contar scores del jugador
        sc = await db.execute(
            select(Score).where(Score.round_id == round_.id, Score.user_id == current_user.id)
        )
        scores = sc.scalars().all()
        total = sum(s.gross_score for s in scores if s.gross_score)
        out.append({
            "id": str(round_.id),
            "name": round_.name,
            "course_id": str(round_.course_id) if round_.course_id else None,
            "course_name": course.name if course else None,
            "game_format": round_.game_format,
            "status": round_.status,
            "holes_to_play": round_.holes_to_play,
            "scheduled_at": round_.scheduled_at.isoformat(),
            "started_at": round_.started_at.isoformat() if round_.started_at else None,
            "finished_at": round_.finished_at.isoformat() if round_.finished_at else None,
            "holes_played": len(scores),
            "total_gross": total if scores else None,
        })
    return out


@router.get("/{round_id}/players")
async def get_round_players(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id)
    )
    rows = result.all()
    return [
        {
            "user_id": str(rp.user_id),
            "first_name": u.first_name,
            "last_name": u.last_name,
            "username": u.username,
            "handicap_index": float(rp.handicap_index) if rp.handicap_index else None,
            "course_handicap": rp.course_handicap,
            "tee_color": rp.tee_color,
            "in_bet": rp.in_bet,
            "status": rp.status,
            "participant_mode": rp.participant_mode,
            "withdrawn_at": rp.withdrawn_at.isoformat() if rp.withdrawn_at else None,
            "withdrawn_reason": rp.withdrawn_reason,
        }
        for rp, u in rows
    ]


@router.patch("/{round_id}/my-tee")
async def set_my_tee(round_id: uuid.UUID, current_user: CurrentUser, db: DB, tee_color: str):
    valid = {"black", "blue", "white", "red"}
    if tee_color not in valid:
        raise HTTPException(status_code=400, detail=f"Tee inválido. Opciones: {', '.join(valid)}")
    result = await db.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_id,
            RoundPlayer.user_id == current_user.id,
        )
    )
    rp = result.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="No eres jugador de esta ronda")
    rp.tee_color = tee_color

    # Calcular Course Handicap: CH = HI × (Slope/113) + (CR − Par)
    if current_user.handicap_index is not None:
        round_result = await db.execute(select(Round).where(Round.id == round_id))
        round_ = round_result.scalar_one_or_none()
        if round_ and round_.course_id:
            course_result = await db.execute(select(Course).where(Course.id == round_.course_id))
            course = course_result.scalar_one_or_none()
            if course and course.slope_rating and course.course_rating and course.par_total:
                ch = round(
                    float(current_user.handicap_index) * (course.slope_rating / 113)
                    + (float(course.course_rating) - course.par_total)
                )
                rp.course_handicap = max(0, ch)

    return {"message": "Tee actualizado", "tee_color": tee_color, "course_handicap": rp.course_handicap}


@router.patch("/{round_id}/my-bet-opt")
async def set_my_bet_opt(round_id: uuid.UUID, in_bet: bool, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_id,
            RoundPlayer.user_id == current_user.id,
        )
    )
    rp = result.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="No eres jugador de esta ronda")
    rp.in_bet = in_bet
    return {"in_bet": in_bet}


@router.get("/{round_id}/bet-config")
async def get_bet_config(round_id: uuid.UUID, db: DB):
    result = await db.execute(select(RoundBetConfig).where(RoundBetConfig.round_id == round_id))
    cfg = result.scalar_one_or_none()
    if not cfg:
        return None
    return {
        "entry_fee": float(cfg.entry_fee),
        "nassau_enabled": cfg.nassau_enabled,
        "nassau_front9": float(cfg.nassau_front9),
        "nassau_back9": float(cfg.nassau_back9),
        "nassau_total": float(cfg.nassau_total),
        "per_hole_bet": float(cfg.per_hole_bet),
        "point_value": float(cfg.point_value),
        "birdie_prize": float(cfg.birdie_prize),
        "eagle_prize": float(cfg.eagle_prize),
        "hole_in_one_prize": float(cfg.hole_in_one_prize),
        "three_putt_penalty": float(cfg.three_putt_penalty),
        "oyes_enabled": cfg.oyes_enabled,
        "oyes_prize": float(cfg.oyes_prize),
        "oyes_accumulates": cfg.oyes_accumulates,
        "skins_enabled": cfg.skins_enabled,
        "skins_value": float(cfg.skins_value),
        "skins_use_net": cfg.skins_use_net,
    }


@router.get("/{round_id}/skins")
async def get_skins(round_id: uuid.UUID, db: DB):
    """Calcula el estado de skines hoyo por hoyo con carry-overs."""
    from app.models.score import Score

    # Obtener config de apuesta
    cfg_result = await db.execute(select(RoundBetConfig).where(RoundBetConfig.round_id == round_id))
    cfg = cfg_result.scalar_one_or_none()
    if not cfg or not cfg.skins_enabled:
        raise HTTPException(status_code=404, detail="Skines no configurados en esta ronda")

    # Jugadores en la apuesta
    players_result = await db.execute(
        select(RoundPlayer).where(RoundPlayer.round_id == round_id, RoundPlayer.in_bet == True)
    )
    players = players_result.scalars().all()
    player_ids = [p.user_id for p in players]
    if not player_ids:
        return {"skins": [], "totals": {}, "pot_remaining": 0}

    # Obtener ronda para holes_to_play
    round_result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_result.scalar_one_or_none()

    # Obtener todos los scores
    scores_result = await db.execute(
        select(Score).where(Score.round_id == round_id, Score.user_id.in_(player_ids))
    )
    all_scores = scores_result.scalars().all()

    # Agrupar por hoyo
    hole_scores: dict[int, dict] = {}
    for s in all_scores:
        h = s.hole_number
        if h not in hole_scores:
            hole_scores[h] = {}
        hole_scores[h][str(s.user_id)] = s.net_score if cfg.skins_use_net else s.gross_score

    n_players = len(player_ids)
    skin_value = float(cfg.skins_value) * n_players  # pot total por hoyo
    holes_total = round_.holes_to_play if round_ else 18

    skins = []
    carry = 0  # hoyos acumulados sin ganar
    totals: dict[str, float] = {str(pid): 0.0 for pid in player_ids}
    pot_remaining = 0.0

    for h in range(1, holes_total + 1):
        scores = hole_scores.get(h, {})
        played_count = len(scores)
        pot_this = skin_value * (carry + 1)

        if played_count < n_players:
            # Hoyo no jugado por todos aún
            skins.append({"hole": h, "status": "pending", "winner_id": None, "pot": pot_this, "carry": carry})
            continue

        valid = {pid: sc for pid, sc in scores.items() if sc is not None}
        if not valid:
            skins.append({"hole": h, "status": "no_score", "winner_id": None, "pot": pot_this, "carry": carry})
            continue

        min_score = min(valid.values())
        winners = [pid for pid, sc in valid.items() if sc == min_score]

        if len(winners) == 1:
            winner_id = winners[0]
            totals[winner_id] = totals.get(winner_id, 0) + pot_this
            skins.append({"hole": h, "status": "won", "winner_id": winner_id, "pot": pot_this, "carry": carry, "score": min_score})
            carry = 0
        else:
            # Empate — carry over
            skins.append({"hole": h, "status": "tie", "winner_id": None, "pot": pot_this, "carry": carry, "tied_players": winners, "score": min_score})
            carry += 1

    # Si quedan carry-overs al final
    if carry > 0:
        pot_remaining = skin_value * carry

    return {
        "skins": skins,
        "totals": totals,
        "pot_remaining": pot_remaining,
        "skin_value": skin_value,
        "use_net": cfg.skins_use_net,
    }


def _calc_ch(handicap_index: Optional[float], course: Optional[Course]) -> Optional[int]:
    """WHS course handicap: CH = HI × (Slope/113) + (CR − Par)"""
    if handicap_index is None or course is None:
        return None
    if not (course.slope_rating and course.course_rating and course.par_total):
        return None
    ch = round(float(handicap_index) * (course.slope_rating / 113)
               + (float(course.course_rating) - course.par_total))
    return max(0, ch)


@router.post("", response_model=RoundOut, status_code=status.HTTP_201_CREATED)
async def create_round(data: RoundCreate, current_user: CurrentUser, db: DB):
    course_res = await db.execute(select(Course).where(Course.id == data.course_id, Course.is_active == True))
    course = course_res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Campo no encontrado")

    # Si la ronda es de un grupo, el creador debe ser miembro activo
    if data.group_id is not None:
        member = await db.scalar(
            select(GroupMember).where(
                GroupMember.group_id == data.group_id,
                GroupMember.user_id == current_user.id,
                GroupMember.status == "active",
            )
        )
        if not member:
            raise HTTPException(status_code=403, detail="No eres miembro de ese grupo")

    alphabet = string.ascii_uppercase + string.digits
    invite_code = ''.join(secrets.choice(alphabet) for _ in range(8))
    round_ = Round(created_by=current_user.id, invite_code=invite_code, **data.model_dump())
    db.add(round_)
    await db.flush()

    # El creador entra como jugador confirmado con tee blanca por defecto
    player = RoundPlayer(
        round_id=round_.id,
        user_id=current_user.id,
        handicap_index=current_user.handicap_index,
        course_handicap=_calc_ch(current_user.handicap_index, course),
        tee_color='white',
        status="confirmed",
    )
    db.add(player)

    # Balance inicial
    balance = RoundPlayerBalance(round_id=round_.id, user_id=current_user.id)
    db.add(balance)

    return round_


@router.get("/{round_id}", response_model=RoundOut)
async def get_round(round_id: uuid.UUID, db: DB):
    result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=404, detail="Jugada no encontrada")
    return round_


@router.patch("/{round_id}", response_model=RoundOut)
async def update_round(round_id: uuid.UUID, data: RoundUpdate, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id, Round.status == "scheduled")
    )
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede editar una ronda programada")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(round_, field, value)
    return round_


@router.patch("/{round_id}/format", response_model=RoundOut)
async def update_round_format(round_id: uuid.UUID, data: dict, current_user: CurrentUser, db: DB):
    """Cambia solo el game_format de una ronda. Permitido en cualquier estado excepto 'finished'.
    Útil para probar diferentes formatos sin resetear scores (stroke ↔ stableford comparten gross)."""
    new_format = data.get("game_format")
    if not new_format:
        raise HTTPException(status_code=422, detail="game_format requerido")
    if new_format not in ("stroke", "stableford", "stableford_modified", "match", "skins", "florida"):
        raise HTTPException(status_code=422, detail=f"Formato inválido: {new_format}")
    result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede cambiar el formato")
    if round_.status == "finished":
        raise HTTPException(status_code=400, detail="No se puede cambiar el formato de una ronda finalizada")
    round_.game_format = new_format
    await db.flush()
    await manager.broadcast_to_round(
        round_id=str(round_id),
        message={"event": "format_changed", "round_id": str(round_id), "game_format": new_format},
    )
    return round_


@router.delete("/{round_id}", status_code=204)
async def delete_round(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id, Round.status == "scheduled")
    )
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede eliminar una ronda programada")
    # Borrar registros relacionados
    await db.execute(
        select(RoundPlayer).where(RoundPlayer.round_id == round_id)
    )
    from sqlalchemy import delete as sql_delete
    await db.execute(sql_delete(RoundPlayer).where(RoundPlayer.round_id == round_id))
    await db.execute(sql_delete(RoundBetConfig).where(RoundBetConfig.round_id == round_id))
    await db.execute(sql_delete(RoundPlayerBalance).where(RoundPlayerBalance.round_id == round_id))
    await db.delete(round_)


@router.post("/{round_id}/bet-config")
async def set_bet_config(round_id: uuid.UUID, data: BetConfigCreate, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Round).where(Round.id == round_id, Round.created_by == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Solo el creador puede configurar apuestas")

    existing = await db.execute(select(RoundBetConfig).where(RoundBetConfig.round_id == round_id))
    cfg = existing.scalar_one_or_none()
    if cfg:
        for field, value in data.model_dump().items():
            setattr(cfg, field, value)
    else:
        db.add(RoundBetConfig(round_id=round_id, **data.model_dump()))

    return {"message": "Configuración de apuestas guardada"}


@router.post("/{round_id}/invite/{user_id}")
async def invite_player(round_id: uuid.UUID, user_id: uuid.UUID, current_user: CurrentUser, db: DB):
    existing = await db.execute(
        select(RoundPlayer).where(RoundPlayer.round_id == round_id, RoundPlayer.user_id == user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Jugador ya en la jugada")

    # Fetch user handicap and course for CH calculation
    user_res = await db.execute(select(User).where(User.id == user_id))
    invited_user = user_res.scalar_one_or_none()
    round_res = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_res.scalar_one_or_none()
    course_ch = None
    if round_ and round_.course_id and invited_user:
        c_res = await db.execute(select(Course).where(Course.id == round_.course_id))
        c = c_res.scalar_one_or_none()
        course_ch = _calc_ch(invited_user.handicap_index, c)

    from datetime import datetime, timezone
    db.add(RoundPlayer(
        round_id=round_id,
        user_id=user_id,
        handicap_index=invited_user.handicap_index if invited_user else None,
        course_handicap=course_ch,
        tee_color='white',
        # Igual que el join por liga: agregar manualmente confirma al jugador.
        # Antes quedaba "invited" sin endpoint para confirmar, por lo que nunca
        # aparecía para capturar score (start/submit/play filtran confirmed/playing).
        status="confirmed",
        confirmed_at=datetime.now(timezone.utc),
    ))
    db.add(RoundPlayerBalance(round_id=round_id, user_id=user_id))
    return {"message": "Jugador agregado"}


@router.post("/{round_id}/start")
async def start_round(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id, Round.status == "scheduled")
    )
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=400, detail="No se puede iniciar esta jugada")

    from datetime import datetime, timezone
    round_.status = "active"
    round_.started_at = datetime.now(timezone.utc)

    # Notificar a los demás jugadores
    players_res = await db.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_id,
            RoundPlayer.status.in_(['confirmed', 'playing']),
        )
    )
    for p in players_res.scalars().all():
        if p.user_id != current_user.id:
            await notify(
                db, p.user_id, 'round_started',
                title='¡Ronda iniciada!',
                body='El organizador ha iniciado la ronda. ¡A jugar!',
                data={'round_id': str(round_id)},
            )

    return {"message": "Jugada iniciada", "round_id": str(round_id)}


@router.post("/{round_id}/scores", response_model=ScoreOut)
async def submit_score(round_id: uuid.UUID, data: ScoreSubmit, current_user: CurrentUser, db: DB):
    # Verificar que la jugada esté activa
    round_result = await db.execute(select(Round).where(Round.id == round_id, Round.status == "active"))
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=400, detail="Jugada no activa")

    # Verificar que el submitter sea jugador confirmado
    my_rp_result = await db.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_id,
            RoundPlayer.user_id == current_user.id,
            RoundPlayer.status.in_(["confirmed", "playing"]),
        )
    )
    my_rp = my_rp_result.scalar_one_or_none()
    if not my_rp:
        raise HTTPException(status_code=403, detail="No eres jugador de esta jugada")

    # Determinar para quién es el score (puede ser para un compañero)
    target_user_id = data.for_user_id if data.for_user_id else current_user.id

    if target_user_id != current_user.id:
        # Captura cruzada
        target_rp_result = await db.execute(
            select(RoundPlayer).where(
                RoundPlayer.round_id == round_id,
                RoundPlayer.user_id == target_user_id,
                RoundPlayer.status.in_(["confirmed", "playing"]),
            )
        )
        target_rp = target_rp_result.scalar_one_or_none()
        if not target_rp:
            raise HTTPException(status_code=404, detail="Jugador objetivo no encontrado en la ronda")

        # Si existen tee_groups en la ronda, validar mismo grupo.
        # Excepción: el creator de la ronda puede capturar para cualquier grupo
        # (override de organizador, útil para torneos y resolución de problemas).
        # Si NO existen tee_groups (legacy), permitir libremente.
        any_group_result = await db.execute(
            select(func.count()).select_from(RoundPlayer)
            .where(RoundPlayer.round_id == round_id, RoundPlayer.tee_group.isnot(None))
        )
        has_any_group = (any_group_result.scalar() or 0) > 0
        is_creator = str(round_.created_by) == str(current_user.id)
        if has_any_group and not is_creator:
            if my_rp.tee_group is None or target_rp.tee_group is None or my_rp.tee_group != target_rp.tee_group:
                raise HTTPException(status_code=403, detail="Solo puedes capturar scores de jugadores en tu mismo grupo de salida")
        rp = target_rp
    else:
        rp = my_rp

    # Enforcement de capturista único: si el grupo del jugador tiene un scorer
    # designado, SOLO ese scorer puede capturar (incluso sus propios scores).
    # Si el grupo no tiene scorer designado, captura libre como antes (compat legacy).
    # Excepción: el CREATOR de la ronda siempre puede capturar (override de organizador
    # — útil cuando el scorer designado no responde o en torneos donde el organizador
    # captura desde la mesa de control).
    if rp.tee_group is not None:
        scorer_res = await db.execute(
            select(RoundPlayer).where(
                RoundPlayer.round_id == round_id,
                RoundPlayer.tee_group == rp.tee_group,
                RoundPlayer.is_group_scorer == True,
            )
        )
        scorer = scorer_res.scalar_one_or_none()
        is_creator = str(round_.created_by) == str(current_user.id)
        if scorer and str(scorer.user_id) != str(current_user.id) and not is_creator:
            raise HTTPException(
                status_code=403,
                detail=f"Solo el capturista designado del grupo puede registrar scores. Si necesitas tomar el control, usa el botón 'Tomar captura'.",
            )

    # Obtener par y stroke_index del hoyo
    hole_result = await db.execute(
        select(CourseHole).where(
            CourseHole.course_id == round_.course_id,
            CourseHole.hole_number == data.hole_number,
        )
    )
    hole = hole_result.scalar_one_or_none()
    if not hole:
        raise HTTPException(status_code=404, detail=f"Hoyo {data.hole_number} no configurado en el campo")

    course_handicap = rp.course_handicap or 0
    stroke_index = hole.stroke_index or data.hole_number

    # Buscar score existente o crear nuevo
    score_result = await db.execute(
        select(Score).where(
            Score.round_id == round_id,
            Score.user_id == target_user_id,
            Score.hole_number == data.hole_number,
        )
    )
    score = score_result.scalar_one_or_none()

    conflict_detected = False
    if not score:
        # Primer registro del score
        score = Score(round_id=round_id, user_id=target_user_id, hole_number=data.hole_number,
                      entered_by=current_user.id)
        db.add(score)
        scoring_svc.apply_score_to_model(score, data, hole.par, stroke_index, course_handicap, round_.game_format, round_.max_handicap)
    else:
        # Score ya existe — detectar conflicto
        if (score.entered_by and str(score.entered_by) != str(current_user.id)
                and score.gross_score != data.gross_score):
            # Persona distinta entra valor diferente → conflicto
            score.conflict_score = data.gross_score
            score.conflict_entered_by = current_user.id
            score.has_conflict = True
            conflict_detected = True
        else:
            # Mismo que ingresó antes, o no había entered_by → actualizar limpiamente
            scoring_svc.apply_score_to_model(score, data, hole.par, stroke_index, course_handicap, round_.game_format, round_.max_handicap)
            score.entered_by = current_user.id
            score.has_conflict = False
            score.conflict_score = None
            score.conflict_entered_by = None

    await db.flush()
    await db.refresh(score)

    # Broadcast — distinto evento si es conflicto
    if conflict_detected:
        await manager.broadcast_to_round(
            round_id=str(round_id),
            message={
                "event": "score_conflict",
                "user_id": str(target_user_id),
                "hole": data.hole_number,
                "score_a": score.gross_score,
                "score_b": data.gross_score,
            },
        )
    else:
        await manager.broadcast_to_round(
            round_id=str(round_id),
            message={
                "event": "score_update",
                "user_id": str(target_user_id),
                "hole": data.hole_number,
                "gross": data.gross_score,
                "net": score.net_score,
                "is_birdie": score.is_birdie,
                "is_eagle": score.is_eagle,
                "is_hole_in_one": score.is_hole_in_one,
                "has_conflict": conflict_detected,
            },
        )

    return score


@router.post("/{round_id}/finish")
async def finish_round(round_id: uuid.UUID, current_user: CurrentUser, db: DB, force: bool = False):
    """Cierra una ronda. Dos comportamientos según contexto:

    - Si hay capturistas designados (is_group_scorer=True) → mueve a `pending_validation`
      y cada jugador debe firmar su tarjeta antes de poder finalizar definitivamente.
      Una segunda llamada al endpoint con status='pending_validation' hace el cierre real.
    - Si no hay capturistas (ronda legacy) → cierra directamente a `finished` (comportamiento previo).
    """
    result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id, Round.status.in_(["active", "pending_validation"]))
    )
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=400, detail="No se puede finalizar esta jugada")

    # Block finish if there are unresolved score conflicts
    from app.models.score import Score as ScoreModel
    conflict_result = await db.execute(
        select(ScoreModel).where(ScoreModel.round_id == round_id, ScoreModel.has_conflict == True).limit(1)
    )
    if conflict_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Hay conflictos de score sin resolver. Resuelve todos los conflictos antes de finalizar.")

    # Advertir si hay jugadores con scorecard incompleto (a menos que force=true).
    # Excluye: withdrawn (se retiraron) y participant_mode='observer' (no se espera scores).
    if not force:
        players_check = await db.execute(
            select(RoundPlayer, User)
            .join(User, User.id == RoundPlayer.user_id)
            .where(
                RoundPlayer.round_id == round_id,
                RoundPlayer.status.in_(["confirmed", "playing", "finished"]),
                RoundPlayer.participant_mode == "playing",
            )
        )
        incomplete = []
        for rp, u in players_check.all():
            sc = await db.execute(
                select(func.count()).select_from(ScoreModel)
                .where(ScoreModel.round_id == round_id, ScoreModel.user_id == rp.user_id)
            )
            n = sc.scalar() or 0
            if n < round_.holes_to_play:
                incomplete.append({
                    "user_id": str(rp.user_id),
                    "name": f"{u.first_name} {u.last_name}",
                    "holes_logged": n,
                    "holes_total": round_.holes_to_play,
                })
        if incomplete:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "incomplete_players",
                    "message": "Hay jugadores con scorecard incompleto. Reenvía con force=true para finalizar de todos modos.",
                    "incomplete": incomplete,
                },
            )

    from datetime import datetime, timezone

    # ¿Esta ronda usa el flujo de validación con capturista único?
    has_scorer_res = await db.execute(
        select(func.count()).select_from(RoundPlayer)
        .where(RoundPlayer.round_id == round_id, RoundPlayer.is_group_scorer == True)
    )
    has_scorer = (has_scorer_res.scalar() or 0) > 0

    # Fase 1: ronda 'active' con capturista → mover a 'pending_validation'
    if round_.status == "active" and has_scorer:
        round_.status = "pending_validation"
        await db.flush()
        await manager.broadcast_to_round(
            round_id=str(round_id),
            message={"event": "pending_validation", "round_id": str(round_id)},
        )
        return {
            "status": "pending_validation",
            "message": "Ronda lista para validación. Cada jugador debe firmar su tarjeta.",
        }

    # Fase 2: ronda 'pending_validation' → verificar firmas pendientes
    if round_.status == "pending_validation":
        pending_res = await db.execute(
            select(RoundPlayer, User)
            .join(User, User.id == RoundPlayer.user_id)
            .where(
                RoundPlayer.round_id == round_id,
                RoundPlayer.status.in_(["confirmed", "playing", "finished"]),
                RoundPlayer.participant_mode == "playing",
                RoundPlayer.score_validated_at.is_(None),
            )
        )
        pending = [
            {"user_id": str(rp.user_id), "name": f"{u.first_name} {u.last_name}"}
            for rp, u in pending_res.all()
        ]
        if pending and not force:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "pending_validations",
                    "message": "Faltan firmas de jugadores. Reenvía con force=true para cerrar sin esperar.",
                    "pending": pending,
                },
            )

    round_.status = "finished"
    round_.finished_at = datetime.now(timezone.utc)
    await db.flush()

    # Persistir balances finales en round_player_balance (para historial financiero)
    try:
        await balances_svc.persist_balances(str(round_id), db)
    except Exception as ex:
        # No-fatal: log y continúa (el cálculo on-demand sigue funcionando si la persistencia falla)
        import logging
        logging.warning(f"persist_balances failed for round {round_id}: {ex}")

    # Recalcular hándicap si la jugada es válida.
    # Excluye withdrawn y observers — esos jugadores no generan differential.
    if round_.is_handicap_valid:
        players_result = await db.execute(
            select(RoundPlayer).where(
                RoundPlayer.round_id == round_id,
                RoundPlayer.status.in_(["confirmed", "playing", "finished"]),
                RoundPlayer.participant_mode == "playing",
            )
        )
        players = players_result.scalars().all()

        course_result = await db.execute(select(Course).where(Course.id == round_.course_id))
        course = course_result.scalar_one_or_none()

        if course and course.course_rating and course.slope_rating:
            for p in players:
                scores_result = await db.execute(
                    select(Score).where(Score.round_id == round_id, Score.user_id == p.user_id)
                )
                scores = scores_result.scalars().all()
                if len(scores) >= round_.holes_to_play:
                    ags = sum(s.gross_score for s in scores if s.gross_score)
                    diff = hcp_svc.calculate_differential(ags, float(course.course_rating), course.slope_rating)
                    db.add(ScoreDifferential(
                        user_id=p.user_id,
                        round_id=round_id,
                        course_id=round_.course_id,
                        adjusted_gross_score=ags,
                        course_rating=float(course.course_rating),
                        slope_rating=course.slope_rating,
                        differential=diff,
                        played_at=round_.finished_at.date(),
                        is_nine_hole=(round_.holes_to_play == 9),
                    ))
                    await db.flush()
                    old_hcp = float(p.handicap_index) if p.handicap_index else None
                    await hcp_svc.recalculate_handicap(str(p.user_id), db)

                    # Leer nuevo HCP y notificar si cambió
                    await db.flush()
                    user_res = await db.execute(select(User).where(User.id == p.user_id))
                    user_ = user_res.scalar_one_or_none()
                    if user_ and user_.handicap_index is not None:
                        new_hcp = float(user_.handicap_index)
                        if old_hcp is not None and abs(new_hcp - old_hcp) >= 0.1:
                            direction = '↓' if new_hcp < old_hcp else '↑'
                            await notify(
                                db, p.user_id, 'handicap_updated',
                                title='Hándicap actualizado',
                                body=f'Tu HCP cambió de {old_hcp:.1f} a {new_hcp:.1f} {direction}',
                                data={'round_id': str(round_id), 'old_hcp': old_hcp, 'new_hcp': new_hcp},
                            )

    # Notificar a todos los jugadores que la ronda terminó
    all_players_res = await db.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_id,
            RoundPlayer.status.in_(['confirmed', 'playing', 'finished']),
        )
    )
    for p in all_players_res.scalars().all():
        if p.user_id != current_user.id:
            await notify(
                db, p.user_id, 'round_finished',
                title='Ronda finalizada',
                body='El organizador ha finalizado la ronda.',
                data={'round_id': str(round_id)},
            )

    return {"message": "Jugada finalizada", "round_id": str(round_id)}


@router.post("/{round_id}/reopen")
async def reopen_round(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Reabre una ronda finalizada (solo creator). Revierte los differentials generados
    por el finish y recalcula los hándicaps afectados."""
    result = await db.execute(
        select(Round).where(
            Round.id == round_id,
            Round.created_by == current_user.id,
            Round.status == "finished",
        )
    )
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=400, detail="Solo el creador puede reabrir una ronda finalizada")

    # Buscar diferenciales generados por este finish (para recalcular HCP después)
    diffs_res = await db.execute(
        select(ScoreDifferential.user_id).where(ScoreDifferential.round_id == round_id)
    )
    affected_user_ids = [row[0] for row in diffs_res.all()]

    # Borrar diferenciales de esta ronda
    await db.execute(delete(ScoreDifferential).where(ScoreDifferential.round_id == round_id))

    # Borrar balances persistidos (ya no son finales)
    try:
        await balances_svc.delete_persisted_balances(str(round_id), db)
    except Exception as ex:
        import logging
        logging.warning(f"delete_persisted_balances failed for round {round_id}: {ex}")

    # Reabrir
    round_.status = "active"
    round_.finished_at = None
    await db.flush()

    # Recalcular hándicap de cada jugador afectado
    for uid in affected_user_ids:
        await hcp_svc.recalculate_handicap(str(uid), db)

    # Broadcast WS
    await manager.broadcast_to_round(
        round_id=str(round_id),
        message={"event": "round_reopened", "round_id": str(round_id)},
    )

    return {
        "message": "Ronda reabierta",
        "round_id": str(round_id),
        "differentials_removed": len(affected_user_ids),
    }


@router.post("/{round_id}/reset")
async def reset_round(
    round_id: uuid.UUID,
    current_user: CurrentUser,
    db: DB,
    clear_tee_groups: bool = False,
    clear_teams: bool = False,
    clear_scorers: bool = False,
):
    """Reset agresivo de una ronda (solo creator). Para iteración de pruebas.

    Borra siempre:
    - Todos los scores de la ronda
    - Resultados de apuestas por hoyo
    - Balances de jugadores
    - Firmas de validación
    - Estados de retiro/observer (regresan a playing)
    - ScoreDifferential generados por la ronda (recalcula HCP afectados)

    Opcionalmente (flags):
    - clear_tee_groups: borra tee_group y starting_hole de todos los jugadores
    - clear_teams: borra team_number, tee_order y match_order de todos los jugadores
    - clear_scorers: borra is_group_scorer de todos los jugadores

    Siempre mantiene:
    - Jugadores invitados, course, formato, apuestas, HCP, tee color
    - Plantillas de teams_published se respeta (no toca)

    Reset:
    - status → scheduled, started_at / finished_at → null
    """
    from sqlalchemy import update as sql_update
    from app.models.score import Score as ScoreModel, HoleBetResult, RoundPlayerBalance

    result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede resetear esta ronda")

    # Capturar usuarios con differentials para recalcular HCP después
    diffs_res = await db.execute(
        select(ScoreDifferential.user_id).where(ScoreDifferential.round_id == round_id)
    )
    affected_user_ids = [row[0] for row in diffs_res.all()]

    # Borrar datos generados durante la ronda (siempre)
    await db.execute(delete(ScoreModel).where(ScoreModel.round_id == round_id))
    await db.execute(delete(HoleBetResult).where(HoleBetResult.round_id == round_id))
    await db.execute(delete(RoundPlayerBalance).where(RoundPlayerBalance.round_id == round_id))
    await db.execute(delete(ScoreDifferential).where(ScoreDifferential.round_id == round_id))

    # Resetear flags por jugador (mantiene grupos, capturistas, tee colors, hcp por defecto)
    base_values = dict(
        score_validated_at=None,
        withdrawn_at=None,
        withdrawn_reason=None,
        participant_mode="playing",
    )
    # Limpiezas opcionales según flags
    if clear_tee_groups:
        base_values.update(tee_group=None, starting_hole=None)
    if clear_teams:
        base_values.update(team_number=None, tee_order=None, match_order=None)
    if clear_scorers:
        base_values.update(is_group_scorer=False)

    await db.execute(
        sql_update(RoundPlayer)
        .where(RoundPlayer.round_id == round_id)
        .values(**base_values)
    )

    # Si se vaciaron teams y la ronda los tenía publicados, marcar como no publicados
    if clear_teams and getattr(round_, "teams_published", False):
        round_.teams_published = False

    # Recrear balance vacío por jugador (mantiene contrato del modelo)
    players_res = await db.execute(
        select(RoundPlayer.user_id).where(RoundPlayer.round_id == round_id)
    )
    for (uid,) in players_res.all():
        db.add(RoundPlayerBalance(round_id=round_id, user_id=uid))

    # Resetear el round
    round_.status = "scheduled"
    round_.started_at = None
    round_.finished_at = None
    await db.flush()

    # Recalcular HCP de los afectados
    for uid in affected_user_ids:
        await hcp_svc.recalculate_handicap(str(uid), db)

    await manager.broadcast_to_round(
        round_id=str(round_id),
        message={
            "event": "round_reset",
            "round_id": str(round_id),
            "cleared": {
                "tee_groups": clear_tee_groups,
                "teams": clear_teams,
                "scorers": clear_scorers,
            },
        },
    )

    return {
        "message": "Ronda reseteada al estado inicial",
        "round_id": str(round_id),
        "handicaps_recalculated": len(affected_user_ids),
        "cleared": {
            "tee_groups": clear_tee_groups,
            "teams": clear_teams,
            "scorers": clear_scorers,
        },
    }


@router.get("/{round_id}/scoreboard")
async def get_scoreboard(round_id: uuid.UUID, db: DB):
    players_result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id)
    )
    rows = players_result.all()

    board = []
    for p, u in rows:
        scores_result = await db.execute(
            select(Score)
            .where(Score.round_id == round_id, Score.user_id == p.user_id)
            .order_by(Score.hole_number)
        )
        scores = scores_result.scalars().all()
        total_gross = sum(s.gross_score for s in scores if s.gross_score)
        total_net = sum(s.net_score for s in scores if s.net_score)
        total_stableford = sum(s.stableford_points for s in scores if s.stableford_points)
        thru = max((s.hole_number for s in scores), default=0)
        board.append({
            "user_id": str(p.user_id),
            "first_name": u.first_name,
            "last_name": u.last_name,
            "course_handicap": p.course_handicap,
            "team_number": p.team_number,
            "status": p.status,
            "participant_mode": p.participant_mode,
            "withdrawn_at": p.withdrawn_at.isoformat() if p.withdrawn_at else None,
            "withdrawn_reason": p.withdrawn_reason,
            "holes_played": len(scores),
            "thru": thru,
            "total_gross": total_gross,
            "total_net": total_net,
            "total_stableford": total_stableford,
            "scores": [
                {
                    "hole": s.hole_number,
                    "gross": s.gross_score,
                    "net": s.net_score,
                    "stableford": s.stableford_points,
                }
                for s in scores
            ],
        })

    return sorted(board, key=lambda x: x["total_gross"] if x["total_gross"] else 999)


@router.get("/{round_id}/balances")
async def get_balances(round_id: uuid.UUID, current_user: CurrentUser, db: DB, lang: str = "es"):
    """Calcula pérdidas y ganancias por jugador.

    Privacidad:
    - Creator/superadmin: ve TODO (líneas completas con amounts de todos los jugadores).
    - Jugador regular: solo ve las líneas que le afectan, con amount filtrado a su propio
      monto. La lista `players` siempre se devuelve completa (para que cualquiera audite
      la tabla de Gran Total y vea cuánto le toca cobrar/pagar a cada uno).

    Reglas implementadas:
    - Entry fee 60/30/10 a low net
    - Nassau F9/B9/Total: pot por segmento, ganador low net toma todo
    - Por hoyo ganado: low net del hoyo cobra a los que pierden
    - Birdie/Eagle/HIO: cada uno paga al que lo hizo
    - 3-putt: el penalizado paga al resto
    - Skins con carry-over en empate (gross o net según config)
    """
    # Validar lang
    lang = "en" if lang == "en" else "es"
    result = await balances_svc.compute_balances(str(round_id), db, lang=lang)

    # Detectar rol del visualizador
    round_res = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_res.scalar_one_or_none()
    is_creator = bool(round_ and str(round_.created_by) == str(current_user.id))
    is_superadmin = bool(getattr(current_user, "is_superadmin", False))
    can_see_all = is_creator or is_superadmin

    # Anotar el role al response
    result["viewer_is_creator"] = is_creator
    result["viewer_is_superadmin"] = is_superadmin
    result["viewer_user_id"] = str(current_user.id)

    # Si NO puede ver todo, filtrar líneas
    if not can_see_all and result.get("has_bets"):
        uid = str(current_user.id)
        filtered: list[dict] = []
        for line in result.get("lines", []):
            my_amount = float(line["amounts"].get(uid, 0) or 0)
            if abs(my_amount) > 0.01:
                filtered.append({
                    "kind": line["kind"],
                    "detail": line["detail"],
                    "amounts": {uid: my_amount},  # solo mi monto, no expone otros
                })
        result["lines"] = filtered

    return result


@router.get("/join/{invite_code}")
async def get_round_by_invite(invite_code: str, db: DB):
    result = await db.execute(
        select(Round, Course)
        .outerjoin(Course, Course.id == Round.course_id)
        .where(Round.invite_code == invite_code)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Código de invitación inválido")
    round_, course = row
    players_result = await db.execute(
        select(RoundPlayer).where(RoundPlayer.round_id == round_.id)
    )
    player_count = len(players_result.scalars().all())
    return {
        "id": str(round_.id),
        "name": round_.name,
        "course_name": course.name if course else None,
        "game_format": round_.game_format,
        "status": round_.status,
        "holes_to_play": round_.holes_to_play,
        "scheduled_at": round_.scheduled_at.isoformat(),
        "player_count": player_count,
        "invite_code": round_.invite_code,
        "notes": round_.notes,
    }


@router.post("/join/{invite_code}")
async def join_round_by_invite(invite_code: str, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Round).where(Round.invite_code == invite_code))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=404, detail="Código de invitación inválido")
    if round_.status == "finished":
        raise HTTPException(status_code=400, detail="Esta jugada ya finalizó")

    existing = await db.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_.id,
            RoundPlayer.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Ya eres parte de esta jugada", "round_id": str(round_.id)}

    # Calcular course handicap con tee blanca por defecto
    course_ch = None
    if round_.course_id:
        c_res = await db.execute(select(Course).where(Course.id == round_.course_id))
        c = c_res.scalar_one_or_none()
        course_ch = _calc_ch(current_user.handicap_index, c)

    db.add(RoundPlayer(
        round_id=round_.id,
        user_id=current_user.id,
        handicap_index=current_user.handicap_index,
        course_handicap=course_ch,
        tee_color='white',
        status="confirmed",
    ))
    db.add(RoundPlayerBalance(round_id=round_.id, user_id=current_user.id))

    # Notificar al creador
    if round_.created_by and round_.created_by != current_user.id:
        await notify(
            db, round_.created_by, 'round_invite',
            title='Nuevo jugador',
            body=f'{current_user.first_name} {current_user.last_name} se unió a tu ronda',
            data={'round_id': str(round_.id)},
        )

    return {"message": "Te uniste a la jugada", "round_id": str(round_.id)}


# ─── Team helpers ─────────────────────────────────────────────────────────────

TEAM_COLORS = ['emerald', 'blue', 'amber', 'red']

def _player_dict(rp: RoundPlayer, u: User) -> dict:
    return {
        "player_id": str(rp.id),
        "user_id": str(rp.user_id),
        "name": f"{u.first_name} {u.last_name}",
        "username": u.username,
        "course_handicap": rp.course_handicap,
        "handicap_index": float(rp.handicap_index) if rp.handicap_index else None,
        "team_number": rp.team_number,
        "match_order": rp.match_order,
    }

def _build_teams(rows: list, teams_published: bool) -> dict:
    assigned = [(rp, u) for rp, u in rows if rp.team_number is not None]
    unassigned = [_player_dict(rp, u) for rp, u in rows if rp.team_number is None]
    if not assigned:
        return {"has_teams": False, "teams": [], "unassigned": [_player_dict(rp, u) for rp, u in rows], "teams_published": teams_published}
    teams_map: dict = {}
    for rp, u in assigned:
        tn = rp.team_number
        if tn not in teams_map:
            teams_map[tn] = {
                "team_number": tn,
                "name": f"Equipo {tn}",
                "color": TEAM_COLORS[(tn - 1) % 4],
                "players": [],
                "total_handicap": 0,
            }
        ch = rp.course_handicap if rp.course_handicap is not None else (int(float(rp.handicap_index)) if rp.handicap_index else 0)
        teams_map[tn]["players"].append(_player_dict(rp, u))
        teams_map[tn]["total_handicap"] += ch
    return {
        "has_teams": True,
        "teams": sorted(teams_map.values(), key=lambda t: t["team_number"]),
        "unassigned": unassigned,
        "teams_published": teams_published,
    }


def _hcp_value(rp) -> float:
    """Handicap de juego para balancear: course_handicap; si no, handicap_index; si no, 99."""
    if rp.course_handicap is not None:
        return float(rp.course_handicap)
    return float(rp.handicap_index) if rp.handicap_index else 99.0


def _balanced_assignment(rps: list, num_teams: int) -> tuple:
    """Calcula equipos y grupos de salida balanceados para `rps` (jugadores activos).

    Devuelve (team_by_idx, group_by_idx, rank_by_idx, group_sizes) — todo 0-based,
    alineado al orden de `rps`. team/group/rank se traducen a 1-based al escribir.

    Garantías (cupos divisibles o no, robustas para cualquier N y M>=N):
      - Tamaños de GRUPO de salida difieren a lo más en 1 (ceil(M/N) grupos, grandes primero).
      - Tamaños de EQUIPO difieren a lo más en 1.
      - Un jugador por equipo en cada grupo (no junta compañeros).
      - HCP repartido por snake entre grupos; dentro de cada grupo, los equipos los toman
        los menos cargados (balancea tallas) y se emparejan jugador↔equipo por HCP
        acumulado (el peor HCP al equipo más liviano) → promedio de HCP parejo.
    """
    M = len(rps)
    N = num_teams
    order = sorted(range(M), key=lambda i: _hcp_value(rps[i]))  # asc por HCP
    G = -(-M // N)  # ceil(M/N)
    base, rem_g = divmod(M, G)
    sizes = [base + (1 if g < rem_g else 0) for g in range(G)]  # grandes primero, ej. 10/4 → [4,3,3]

    # PASS 1 — repartir a grupos con snake (HCP balanceado), respetando tamaños
    members: dict = {g: [] for g in range(G)}
    active = list(range(G))
    idx = 0
    rnd = 0
    while idx < M:
        seq = active if rnd % 2 == 0 else active[::-1]
        for g in seq:
            if idx >= M:
                break
            if len(members[g]) < sizes[g]:
                members[g].append(order[idx])
                idx += 1
        active = [g for g in active if len(members[g]) < sizes[g]]
        rnd += 1

    # PASS 2 — equipos: greedy balanceado (tallas <=1 + promedio HCP parejo)
    team_by = [0] * M
    group_by = [0] * M
    rank_by = [0] * M
    team_count = [0] * N
    team_total = [0.0] * N
    for g in sorted(range(G), key=lambda g: -len(members[g])):  # grupos más grandes primero
        ms = members[g]
        s = len(ms)
        # equipos presentes en el grupo = los s con menor conteo (desempate menor total, índice)
        present = sorted(range(N), key=lambda t: (team_count[t], team_total[t], t))[:s]
        players_asc = sorted(ms, key=lambda i: _hcp_value(rps[i]))  # mejor HCP = rank 0
        for r, i in enumerate(players_asc):
            rank_by[i] = r
            group_by[i] = g
        # emparejar: equipo con menor total ← peor HCP (sube los livianos)
        present_by_total = sorted(present, key=lambda t: team_total[t])
        players_desc = players_asc[::-1]
        for k, t in enumerate(present_by_total):
            i = players_desc[k]
            team_by[i] = t
            team_count[t] += 1
            team_total[t] += _hcp_value(rps[i])
    return team_by, group_by, rank_by, sizes


# ─── Teams endpoints ──────────────────────────────────────────────────────────

@router.get("/{round_id}/teams")
async def get_teams(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Returns team assignments. Non-creators only see teams once published."""
    round_result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=404, detail="Jugada no encontrada")

    is_creator = str(round_.created_by) == str(current_user.id)
    published = round_.teams_published

    # Non-creators see nothing until published
    if not is_creator and not published:
        return {"has_teams": False, "teams": [], "unassigned": [], "teams_published": False}

    result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id)
    )
    rows = result.all()
    return _build_teams(rows, published)


@router.post("/{round_id}/teams/generate")
async def generate_teams(round_id: uuid.UUID, num_teams: int = 2, current_user: CurrentUser = ..., db: DB = ...):
    """Arma equipos balanceados por handicap (tallas <=1 + promedio parejo), borrador privado."""
    round_result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede gestionar equipos")
    if not 2 <= num_teams <= 12:
        raise HTTPException(status_code=400, detail="Número de equipos: 2 a 12")

    result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id)
    )
    rows = result.all()
    if len(rows) < num_teams:
        raise HTTPException(status_code=400, detail=f"Se necesitan al menos {num_teams} jugadores")

    # Balanceo por HCP: tallas de equipo <=1 y promedio parejo (mismo motor que el
    # auto-armado, pero aquí solo escribimos el equipo; los grupos de salida no se tocan).
    rps = [rp for rp, _ in rows]
    team_by, _g, _r, _sizes = _balanced_assignment(rps, num_teams)
    for i, rp in enumerate(rps):
        rp.team_number = team_by[i] + 1

    round_.teams_published = False
    await db.flush()

    return _build_teams(rows, False)


@router.post("/{round_id}/auto-setup")
async def auto_setup_format(
    round_id: uuid.UUID,
    current_user: CurrentUser,
    db: DB,
    num_teams: int = 4,
    shotgun: bool = False,
    publish: bool = True,
):
    """Auto-arma el formato Medal Play por equipos en un solo paso:
    - Equipos balanceados por handicap (talla <=1 y promedio HCP parejo).
    - Grupos de salida con UN jugador de cada equipo por grupo (sin compañeros juntos).
    - num_teams = N. Se forman ceil(M/N) grupos de tamaño parejo (difieren <=1);
      en cupos no divisibles NO queda un grupo final chico (10/4 → 4,3,3, no 4,4,2).
    - shotgun: cada grupo arranca en su propio hoyo; si no, todos en el hoyo 1.
    Excluye retirados/observadores (les limpia equipo y grupo). Creador only.
    """
    round_result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede armar el formato")
    if round_.status == "finished":
        raise HTTPException(status_code=400, detail="No se puede modificar una ronda finalizada")
    if not 2 <= num_teams <= 12:
        raise HTTPException(status_code=400, detail="Número de equipos: 2 a 12")

    result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id)
    )
    rows = result.all()
    playing = [(rp, u) for rp, u in rows if rp.participant_mode == "playing" and rp.withdrawn_at is None]
    if len(playing) < num_teams:
        raise HTTPException(status_code=400, detail=f"Se necesitan al menos {num_teams} jugadores activos")

    holes = round_.holes_to_play or 18

    # Equipos + grupos de salida balanceados (tallas <=1, grupos parejos, un jugador por
    # equipo por grupo, promedio HCP parejo). Ver _balanced_assignment.
    playing_rps = [rp for rp, _ in playing]
    team_by, group_by, rank_by, sizes = _balanced_assignment(playing_rps, num_teams)
    for i, rp in enumerate(playing_rps):
        g = group_by[i]
        rp.team_number = team_by[i] + 1
        rp.tee_group = g + 1
        rp.starting_hole = ((g % holes) + 1) if shotgun else 1
        rp.tee_order = rank_by[i]

    # Limpiar a quienes no juegan
    for rp, _ in rows:
        if rp.participant_mode != "playing" or rp.withdrawn_at is not None:
            rp.team_number = None
            rp.tee_group = None
            rp.starting_hole = None

    round_.teams_published = bool(publish)
    await db.flush()

    refreshed = await db.execute(
        select(RoundPlayer, User).join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id)
    )
    rrows = refreshed.all()
    return {
        **_build_teams(rrows, round_.teams_published),
        "num_teams": num_teams,
        "num_groups": len(sizes),
        "players_per_group": max(sizes),
        "last_group_size": min(sizes),
        "group_sizes": sizes,
        "shotgun": shotgun,
    }


@router.put("/{round_id}/teams/assign")
async def assign_player_team(round_id: uuid.UUID, player_id: uuid.UUID, team_number: int, current_user: CurrentUser, db: DB):
    """Moves a player to a different team (creator only, resets published flag)."""
    round_result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede mover jugadores")

    rp_result = await db.execute(
        select(RoundPlayer).where(RoundPlayer.id == player_id, RoundPlayer.round_id == round_id)
    )
    rp = rp_result.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="Jugador no encontrado en esta ronda")

    rp.team_number = team_number
    round_.teams_published = False
    await db.flush()

    result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id)
    )
    return _build_teams(result.all(), False)


@router.delete("/{round_id}/players/{user_id}")
async def remove_player_from_round(round_id: uuid.UUID, user_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Creator removes a player from the round (scheduled or active, not finished)."""
    round_result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede quitar jugadores")
    if round_.status == "finished":
        raise HTTPException(status_code=400, detail="No se puede modificar una ronda finalizada")
    if str(user_id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="El creador no puede quitarse a sí mismo")

    rp_result = await db.execute(
        select(RoundPlayer).where(RoundPlayer.round_id == round_id, RoundPlayer.user_id == user_id)
    )
    rp = rp_result.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="Jugador no encontrado en esta ronda")

    from sqlalchemy import delete as sql_delete
    from app.models.score import Score as ScoreModel
    # Remove scores, balance and player record
    await db.execute(sql_delete(ScoreModel).where(ScoreModel.round_id == round_id, ScoreModel.user_id == user_id))
    await db.execute(sql_delete(RoundPlayerBalance).where(RoundPlayerBalance.round_id == round_id, RoundPlayerBalance.user_id == user_id))
    await db.delete(rp)
    await db.flush()

    # Return updated teams
    result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id)
    )
    return _build_teams(result.all(), round_.teams_published)


@router.patch("/{round_id}/players/{user_id}/handicap")
async def set_player_handicap(
    round_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentUser,
    db: DB,
    course_handicap: int,
    handicap_index: Optional[float] = None,
):
    """El creador fija MANUALMENTE el handicap de juego (golpes de ventaja) de un
    jugador en ESTA jugada — para casos reales: jugadores que no llevan bien su
    handicap o que usan otra app/sistema. Edita round_players.course_handicap (lo
    que usa el scoring). Si la ronda ya tiene scores capturados de ese jugador, los
    recalcula con el nuevo handicap. No toca el handicap index global del usuario.
    """
    round_result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede ajustar el handicap")
    if round_.status == "finished":
        raise HTTPException(status_code=400, detail="No se puede modificar una ronda finalizada")
    if not 0 <= course_handicap <= 54:
        raise HTTPException(status_code=400, detail="Handicap de juego fuera de rango (0–54)")

    rp_res = await db.execute(
        select(RoundPlayer).where(RoundPlayer.round_id == round_id, RoundPlayer.user_id == user_id)
    )
    rp = rp_res.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="Jugador no encontrado en esta jugada")

    rp.course_handicap = course_handicap
    if handicap_index is not None:
        rp.handicap_index = handicap_index

    # Recalcular scores ya capturados de este jugador con el nuevo handicap
    holes_res = await db.execute(select(CourseHole).where(CourseHole.course_id == round_.course_id))
    holes = {h.hole_number: (h.par, h.stroke_index) for h in holes_res.scalars().all()}
    scores_res = await db.execute(
        select(Score).where(Score.round_id == round_id, Score.user_id == user_id)
    )
    eff = scoring_svc.effective_handicap(course_handicap, round_.max_handicap)
    recalculated = 0
    for s in scores_res.scalars().all():
        ph = holes.get(s.hole_number)
        if not ph or s.gross_score is None:
            continue
        par, si = ph
        s.net_score = s.gross_score - scoring_svc.strokes_received(eff, si)
        if round_.game_format in ("stableford", "stableford_modified"):
            s.stableford_points = scoring_svc.calculate_stableford(
                s.gross_score, par, eff, si, round_.game_format == "stableford_modified"
            )
        recalculated += 1

    await db.flush()
    return {
        "user_id": str(user_id),
        "course_handicap": rp.course_handicap,
        "handicap_index": float(rp.handicap_index) if rp.handicap_index is not None else None,
        "scores_recalculated": recalculated,
    }


@router.post("/{round_id}/players/{user_id}/withdraw")
async def withdraw_player(
    round_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentUser,
    db: DB,
    reason: Optional[str] = None,
):
    """Marca un jugador como retirado (WD). Sus scores capturados se preservan, los
    hoyos restantes quedan vacíos, no genera differential, no bloquea el finish."""
    round_result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=404, detail="Ronda no encontrada")
    # Permiso: creator o el propio jugador
    is_creator = str(round_.created_by) == str(current_user.id)
    is_self = str(user_id) == str(current_user.id)
    if not (is_creator or is_self):
        raise HTTPException(status_code=403, detail="Solo el creador o el jugador puede registrar el retiro")
    if round_.status == "finished":
        raise HTTPException(status_code=400, detail="No se puede retirar jugadores de una ronda finalizada")

    rp_res = await db.execute(
        select(RoundPlayer).where(RoundPlayer.round_id == round_id, RoundPlayer.user_id == user_id)
    )
    rp = rp_res.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="Jugador no encontrado en la ronda")

    from datetime import datetime, timezone
    rp.status = "withdrawn"
    rp.withdrawn_at = datetime.now(timezone.utc)
    rp.withdrawn_reason = (reason or "")[:200] if reason else None
    await db.flush()

    await manager.broadcast_to_round(
        round_id=str(round_id),
        message={"event": "player_withdrawn", "user_id": str(user_id), "reason": rp.withdrawn_reason},
    )

    # Notificar a otros jugadores
    other_res = await db.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_id,
            RoundPlayer.user_id != user_id,
            RoundPlayer.status.in_(["confirmed", "playing", "finished"]),
        )
    )
    user_res = await db.execute(select(User).where(User.id == user_id))
    wd_user = user_res.scalar_one_or_none()
    wd_name = f"{wd_user.first_name} {wd_user.last_name}" if wd_user else "Un jugador"
    for p in other_res.scalars().all():
        await notify(
            db, p.user_id, 'player_withdrawn',
            title='Jugador retirado',
            body=f'{wd_name} se retiró de la ronda{(" (" + rp.withdrawn_reason + ")") if rp.withdrawn_reason else ""}.',
            data={'round_id': str(round_id), 'user_id': str(user_id)},
        )

    return {"message": "Jugador retirado", "user_id": str(user_id), "withdrawn_at": rp.withdrawn_at.isoformat()}


@router.post("/{round_id}/players/{user_id}/unwithdraw")
async def unwithdraw_player(round_id: uuid.UUID, user_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Revierte el retiro (creator o el propio jugador)."""
    round_result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=404, detail="Ronda no encontrada")
    is_creator = str(round_.created_by) == str(current_user.id)
    is_self = str(user_id) == str(current_user.id)
    if not (is_creator or is_self):
        raise HTTPException(status_code=403, detail="Solo el creador o el jugador puede deshacer el retiro")
    if round_.status == "finished":
        raise HTTPException(status_code=400, detail="No se puede modificar una ronda finalizada")

    rp_res = await db.execute(
        select(RoundPlayer).where(RoundPlayer.round_id == round_id, RoundPlayer.user_id == user_id)
    )
    rp = rp_res.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="Jugador no encontrado en la ronda")
    if rp.status != "withdrawn":
        return {"message": "El jugador no estaba retirado", "user_id": str(user_id)}

    rp.status = "playing" if round_.status == "active" else "confirmed"
    rp.withdrawn_at = None
    rp.withdrawn_reason = None
    await db.flush()
    return {"message": "Retiro revertido", "user_id": str(user_id)}


@router.post("/{round_id}/players/{user_id}/set-mode")
async def set_participant_mode(
    round_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentUser,
    db: DB,
    mode: str,
):
    """Cambia el participant_mode entre 'playing' y 'observer'.
    Observer = jugador en la lista pero no se espera que tenga scores."""
    if mode not in ("playing", "observer"):
        raise HTTPException(status_code=400, detail="Modo inválido. Usa 'playing' u 'observer'.")

    round_result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=404, detail="Ronda no encontrada")
    is_creator = str(round_.created_by) == str(current_user.id)
    is_self = str(user_id) == str(current_user.id)
    if not (is_creator or is_self):
        raise HTTPException(status_code=403, detail="Solo el creador o el jugador puede cambiar este modo")

    rp_res = await db.execute(
        select(RoundPlayer).where(RoundPlayer.round_id == round_id, RoundPlayer.user_id == user_id)
    )
    rp = rp_res.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="Jugador no encontrado en la ronda")

    rp.participant_mode = mode
    await db.flush()

    await manager.broadcast_to_round(
        round_id=str(round_id),
        message={"event": "participant_mode_changed", "user_id": str(user_id), "mode": mode},
    )
    return {"message": "Modo actualizado", "user_id": str(user_id), "mode": mode}


@router.delete("/{round_id}/teams")
async def clear_teams(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Borra todos los equipos de la ronda (team_number, tee_order, match_order) sin tocar
    scores, balances ni firmas. Solo creator. Resetea teams_published a False.
    """
    round_result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede limpiar equipos")

    await db.execute(
        update(RoundPlayer)
        .where(RoundPlayer.round_id == round_id)
        .values(team_number=None, tee_order=None, match_order=None)
    )
    round_.teams_published = False
    await db.flush()

    await manager.broadcast_to_round(
        round_id=str(round_id),
        message={"event": "teams_cleared"},
    )
    return {"message": "Equipos eliminados", "round_id": str(round_id)}


@router.post("/{round_id}/teams/publish")
async def publish_teams(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Makes teams visible to all players in the round."""
    round_result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede publicar equipos")

    assigned = await db.execute(
        select(RoundPlayer).where(RoundPlayer.round_id == round_id, RoundPlayer.team_number.isnot(None))
    )
    if not assigned.scalars().all():
        raise HTTPException(status_code=400, detail="Genera los equipos primero antes de publicar")

    round_.teams_published = True
    return {"message": "Equipos publicados. Todos los jugadores ya pueden verlos.", "teams_published": True}


@router.put("/{round_id}/teams/reorder")
async def reorder_team_players(
    round_id: uuid.UUID,
    current_user: CurrentUser,
    db: DB,
    orders: list[dict],  # [{player_id: str, match_order: int}, ...]
):
    """Sets match_order for each player within their team (creator only).
    match_order determines head-to-head pairings: same match_order across teams = matchup."""
    round_result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede reordenar jugadores")

    for item in orders:
        pid = item.get("player_id")
        mo = item.get("match_order")
        if pid is None or mo is None:
            continue
        rp_res = await db.execute(
            select(RoundPlayer).where(
                RoundPlayer.id == uuid.UUID(pid),
                RoundPlayer.round_id == round_id,
            )
        )
        rp = rp_res.scalar_one_or_none()
        if rp:
            rp.match_order = mo

    await db.flush()
    result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id)
    )
    return _build_teams(result.all(), round_.teams_published)


def _compute_matchup_state(
    scores_by_player: dict[str, dict[int, int]],
    player1_id: str,
    player2_id: str,
    holes_to_play: int,
) -> dict:
    """
    Computes head-to-head match play state between two players.
    Returns holes_up (+ = p1 ahead), current_hole, status, result_str.
    Uses net scores (or gross if net missing).
    """
    holes_up = 0  # positive = player1 winning
    last_hole_played = 0

    for h in range(1, holes_to_play + 1):
        s1 = scores_by_player.get(player1_id, {}).get(h)
        s2 = scores_by_player.get(player2_id, {}).get(h)
        if s1 is None or s2 is None:
            break
        last_hole_played = h
        if s1 < s2:
            holes_up += 1
        elif s2 < s1:
            holes_up -= 1

    holes_remaining = holes_to_play - last_hole_played
    closed = abs(holes_up) > holes_remaining

    if last_hole_played == 0:
        status = "not_started"
        result_str = "AS"
    elif closed:
        margin = abs(holes_up)
        holes_left = holes_remaining
        # e.g. 3&2
        result_str = f"{margin}&{holes_left}" if holes_left > 0 else f"{margin} UP"
        status = "closed"
    elif last_hole_played == holes_to_play:
        if holes_up == 0:
            status = "halved"
            result_str = "AS"
        else:
            margin = abs(holes_up)
            result_str = f"{margin} UP"
            status = "closed"
    else:
        status = "in_progress"
        if holes_up == 0:
            result_str = "AS"
        elif holes_up > 0:
            result_str = f"{holes_up} UP"
        else:
            result_str = f"{abs(holes_up)} DN"

    winner_side = None
    if status in ("closed", "halved"):
        if holes_up > 0:
            winner_side = "player1"
        elif holes_up < 0:
            winner_side = "player2"

    return {
        "holes_up": holes_up,
        "holes_remaining": holes_remaining,
        "last_hole_played": last_hole_played,
        "status": status,
        "result_str": result_str,
        "winner_side": winner_side,
    }


@router.get("/{round_id}/matchups")
async def get_matchups(round_id: uuid.UUID, db: DB):
    """
    Returns head-to-head matchups for Match Play format.
    Players are paired by match_order (same value across teams = matchup).
    Public endpoint — no auth required.
    """
    round_result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=404, detail="Jugada no encontrada")

    players_result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id, RoundPlayer.team_number.isnot(None))
        .order_by(RoundPlayer.team_number, RoundPlayer.match_order)
    )
    rows = players_result.all()
    if not rows:
        return {"has_matchups": False, "matchups": [], "needs_setup": True}

    # Group by team
    teams_players: dict[int, list] = {}
    for rp, u in rows:
        tn = rp.team_number
        if tn not in teams_players:
            teams_players[tn] = []
        teams_players[tn].append((rp, u))

    if len(teams_players) < 2:
        return {"has_matchups": False, "matchups": [], "needs_setup": True}

    # Check if match_order is set on at least one player
    has_order = any(rp.match_order is not None for rp, _ in rows)
    if not has_order:
        # Auto-assign match_order based on list position
        for tn, players in teams_players.items():
            for i, (rp, _) in enumerate(players):
                rp.match_order = i + 1
        await db.flush()

    # Re-sort by match_order
    for tn in teams_players:
        teams_players[tn].sort(key=lambda x: x[0].match_order if x[0].match_order is not None else 999)

    # Load scores
    from app.models.score import Score as ScoreModel
    scores_result = await db.execute(
        select(ScoreModel).where(ScoreModel.round_id == round_id)
    )
    all_scores = scores_result.scalars().all()

    # Build scores_by_player: {user_id_str: {hole: net_score}}
    scores_by_player: dict[str, dict[int, int]] = {}
    for s in all_scores:
        uid = str(s.user_id)
        score_val = s.net_score if s.net_score is not None else s.gross_score
        if score_val is not None:
            if uid not in scores_by_player:
                scores_by_player[uid] = {}
            scores_by_player[uid][s.hole_number] = score_val

    # Pair up: use team 1 vs team 2 (or first two teams if different numbers)
    team_numbers = sorted(teams_players.keys())
    t1_players = teams_players[team_numbers[0]]
    t2_players = teams_players[team_numbers[1]]
    max_pairs = max(len(t1_players), len(t2_players))

    matchups = []
    for i in range(max_pairs):
        p1_rp, p1_u = t1_players[i] if i < len(t1_players) else (None, None)
        p2_rp, p2_u = t2_players[i] if i < len(t2_players) else (None, None)

        match_num = i + 1
        if p1_rp and p2_rp:
            state = _compute_matchup_state(
                scores_by_player,
                str(p1_rp.user_id),
                str(p2_rp.user_id),
                round_.holes_to_play,
            )
            matchups.append({
                "match_number": match_num,
                "player1": {
                    "player_id": str(p1_rp.id),
                    "user_id": str(p1_rp.user_id),
                    "name": f"{p1_u.first_name} {p1_u.last_name}",
                    "username": p1_u.username,
                    "course_handicap": p1_rp.course_handicap,
                    "team_number": p1_rp.team_number,
                    "match_order": p1_rp.match_order,
                },
                "player2": {
                    "player_id": str(p2_rp.id),
                    "user_id": str(p2_rp.user_id),
                    "name": f"{p2_u.first_name} {p2_u.last_name}",
                    "username": p2_u.username,
                    "course_handicap": p2_rp.course_handicap,
                    "team_number": p2_rp.team_number,
                    "match_order": p2_rp.match_order,
                },
                **state,
            })
        elif p1_rp:
            matchups.append({
                "match_number": match_num,
                "player1": _player_dict(p1_rp, p1_u),
                "player2": None,
                "status": "bye",
                "result_str": "BYE",
                "holes_up": 0,
                "holes_remaining": round_.holes_to_play,
                "winner_side": "player1",
            })
        elif p2_rp:
            matchups.append({
                "match_number": match_num,
                "player1": None,
                "player2": _player_dict(p2_rp, p2_u),
                "status": "bye",
                "result_str": "BYE",
                "holes_up": 0,
                "holes_remaining": round_.holes_to_play,
                "winner_side": "player2",
            })

    team_score = {tn: 0 for tn in team_numbers}
    for m in matchups:
        if m["status"] == "closed":
            if m["winner_side"] == "player1" and m["player1"]:
                team_score[m["player1"]["team_number"]] += 1
            elif m["winner_side"] == "player2" and m["player2"]:
                team_score[m["player2"]["team_number"]] += 1
        elif m["status"] == "halved":
            for tn in team_numbers:
                team_score[tn] += 0.5

    return {
        "has_matchups": True,
        "needs_setup": False,
        "team_numbers": team_numbers,
        "team_score": team_score,
        "matchups": matchups,
        "holes_to_play": round_.holes_to_play,
        "round_status": round_.status,
    }


# ─── Tee groups ──────────────────────────────────────────────────────────────

@router.get("/{round_id}/tee-groups")
async def get_tee_groups(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Returns tee group assignments for the round."""
    result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id)
        .order_by(RoundPlayer.tee_group, RoundPlayer.tee_order)
    )
    rows = result.all()

    groups: dict[int, dict] = {}
    ungrouped = []
    for rp, u in rows:
        p = {
            "player_id": str(rp.id),
            "user_id": str(rp.user_id),
            "name": f"{u.first_name} {u.last_name}",
            "username": u.username,
            "handicap_index": float(rp.handicap_index) if rp.handicap_index is not None else (float(u.handicap_index) if u.handicap_index is not None else None),
            "course_handicap": rp.course_handicap,
            "tee_color": rp.tee_color,
            "tee_group": rp.tee_group,
            "starting_hole": rp.starting_hole,
            "is_group_scorer": rp.is_group_scorer,
            "score_validated_at": rp.score_validated_at.isoformat() if rp.score_validated_at else None,
        }
        if rp.tee_group is not None:
            if rp.tee_group not in groups:
                groups[rp.tee_group] = {
                    "group_number": rp.tee_group,
                    "starting_hole": rp.starting_hole,
                    "players": [],
                    "scorer_user_id": None,
                }
            groups[rp.tee_group]["players"].append(p)
            if rp.is_group_scorer:
                groups[rp.tee_group]["scorer_user_id"] = str(rp.user_id)
        else:
            ungrouped.append(p)

    return {
        "has_groups": len(groups) > 0,
        "groups": sorted(groups.values(), key=lambda g: g["group_number"]),
        "ungrouped": ungrouped,
    }


@router.put("/{round_id}/tee-groups")
async def set_tee_groups(
    round_id: uuid.UUID,
    current_user: CurrentUser,
    db: DB,
    assignments: list[dict],  # [{player_id, tee_group, starting_hole}]
):
    """Batch-assigns tee groups and starting holes. Creator only."""
    round_result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    if not round_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Solo el creador puede asignar grupos de salida")

    for item in assignments:
        pid = item.get("player_id")
        grp = item.get("tee_group")
        hole = item.get("starting_hole", 1)
        if not pid:
            continue
        rp_res = await db.execute(
            select(RoundPlayer).where(
                RoundPlayer.id == uuid.UUID(pid),
                RoundPlayer.round_id == round_id,
            )
        )
        rp = rp_res.scalar_one_or_none()
        if rp:
            rp.tee_group = grp
            rp.starting_hole = hole if grp is not None else None

    await db.flush()

    result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id)
        .order_by(RoundPlayer.tee_group, RoundPlayer.tee_order)
    )
    rows = result.all()
    groups: dict[int, dict] = {}
    ungrouped = []
    for rp, u in rows:
        p = {"player_id": str(rp.id), "user_id": str(rp.user_id),
             "name": f"{u.first_name} {u.last_name}", "username": u.username,
             "handicap_index": float(rp.handicap_index) if rp.handicap_index is not None else (float(u.handicap_index) if u.handicap_index is not None else None),
             "course_handicap": rp.course_handicap, "tee_color": rp.tee_color,
             "tee_group": rp.tee_group, "starting_hole": rp.starting_hole,
             "is_group_scorer": rp.is_group_scorer,
             "score_validated_at": rp.score_validated_at.isoformat() if rp.score_validated_at else None}
        if rp.tee_group is not None:
            if rp.tee_group not in groups:
                groups[rp.tee_group] = {"group_number": rp.tee_group,
                                         "starting_hole": rp.starting_hole, "players": [],
                                         "scorer_user_id": None}
            groups[rp.tee_group]["players"].append(p)
            if rp.is_group_scorer:
                groups[rp.tee_group]["scorer_user_id"] = str(rp.user_id)
        else:
            ungrouped.append(p)
    return {"has_groups": len(groups) > 0,
            "groups": sorted(groups.values(), key=lambda g: g["group_number"]),
            "ungrouped": ungrouped}


# ─── Scorer único por grupo: designar, ceder, tomar control ──────────────────

async def _designate_scorer(db, round_id: uuid.UUID, target_user_id: uuid.UUID):
    """Helper: marca target_user como scorer del grupo y quita el flag al resto del mismo tee_group."""
    target_res = await db.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_id,
            RoundPlayer.user_id == target_user_id,
        )
    )
    target = target_res.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Jugador no está en la ronda")
    if target.tee_group is None:
        raise HTTPException(status_code=400, detail="El jugador debe estar asignado a un grupo de salida")

    # Quitar el flag a los otros del mismo grupo
    from sqlalchemy import update as sql_update
    await db.execute(
        sql_update(RoundPlayer)
        .where(
            RoundPlayer.round_id == round_id,
            RoundPlayer.tee_group == target.tee_group,
            RoundPlayer.user_id != target_user_id,
        )
        .values(is_group_scorer=False)
    )
    target.is_group_scorer = True
    await db.flush()
    return target


@router.patch("/{round_id}/players/{user_id}/set-scorer")
async def set_scorer(round_id: uuid.UUID, user_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Creator designa al capturista único del grupo donde está el jugador target."""
    round_res = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    if not round_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Solo el creador puede designar capturistas")

    target = await _designate_scorer(db, round_id, user_id)

    await manager.broadcast_to_round(
        round_id=str(round_id),
        message={
            "event": "scorer_changed",
            "tee_group": target.tee_group,
            "scorer_user_id": str(user_id),
            "changed_by": "creator",
            "changed_by_user_id": str(current_user.id),
        },
    )
    return {"user_id": str(user_id), "tee_group": target.tee_group, "is_group_scorer": True}


@router.post("/{round_id}/players/me/claim-scorer")
async def claim_scorer(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Cualquier miembro del grupo se autoasigna como capturista. Útil cuando al scorer
    se le acaba la batería o se retira y otro del grupo debe tomar el control."""
    target = await _designate_scorer(db, round_id, current_user.id)

    await manager.broadcast_to_round(
        round_id=str(round_id),
        message={
            "event": "scorer_changed",
            "tee_group": target.tee_group,
            "scorer_user_id": str(current_user.id),
            "changed_by": "self",
            "changed_by_user_id": str(current_user.id),
        },
    )
    return {"user_id": str(current_user.id), "tee_group": target.tee_group, "is_group_scorer": True}


@router.post("/{round_id}/players/me/validate-scorecard")
async def validate_scorecard(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Jugador firma su tarjeta al final de la ronda. Solo válido si round.status == 'pending_validation'."""
    round_res = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_res.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=404, detail="Ronda no encontrada")
    if round_.status != "pending_validation":
        raise HTTPException(status_code=400, detail="La ronda no está en estado de validación")

    rp_res = await db.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_id,
            RoundPlayer.user_id == current_user.id,
        )
    )
    rp = rp_res.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="No estás en esta ronda")

    from datetime import datetime, timezone
    rp.score_validated_at = datetime.now(timezone.utc)
    await db.flush()

    await manager.broadcast_to_round(
        round_id=str(round_id),
        message={
            "event": "scorecard_validated",
            "user_id": str(current_user.id),
            "validated_at": rp.score_validated_at.isoformat(),
        },
    )
    return {"user_id": str(current_user.id), "validated_at": rp.score_validated_at.isoformat()}


@router.get("/{round_id}/conflicts")
async def get_conflicts(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Returns all unresolved score conflicts for this round."""
    from app.models.score import Score as ScoreModel
    result = await db.execute(
        select(ScoreModel, User)
        .join(User, User.id == ScoreModel.user_id)
        .where(ScoreModel.round_id == round_id, ScoreModel.has_conflict == True)
    )
    rows = result.all()
    return [
        {
            "user_id": str(s.user_id),
            "player_name": f"{u.first_name} {u.last_name}",
            "hole_number": s.hole_number,
            "score_a": s.gross_score,
            "score_b": s.conflict_score,
            "entered_by": str(s.entered_by) if s.entered_by else None,
            "conflict_entered_by": str(s.conflict_entered_by) if s.conflict_entered_by else None,
        }
        for s, u in rows
    ]


@router.post("/{round_id}/scores/{hole_number}/resolve")
async def resolve_conflict(
    round_id: uuid.UUID,
    hole_number: int,
    current_user: CurrentUser,
    db: DB,
    correct_score: int,
    target_user_id: Optional[uuid.UUID] = None,
):
    """Resolves a score conflict. The player themselves or the round creator can resolve."""
    from app.models.score import Score as ScoreModel
    uid = target_user_id if target_user_id else current_user.id

    # Only the player themselves or the creator can resolve
    round_res = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_res.scalar_one_or_none()
    is_creator = round_ and str(round_.created_by) == str(current_user.id)
    if str(uid) != str(current_user.id) and not is_creator:
        raise HTTPException(status_code=403, detail="Solo el jugador o el creador puede resolver conflictos")

    score_res = await db.execute(
        select(ScoreModel).where(
            ScoreModel.round_id == round_id,
            ScoreModel.user_id == uid,
            ScoreModel.hole_number == hole_number,
        )
    )
    score = score_res.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="Score no encontrado")

    # Get hole info to recalculate
    rp_res = await db.execute(
        select(RoundPlayer).where(RoundPlayer.round_id == round_id, RoundPlayer.user_id == uid)
    )
    rp = rp_res.scalar_one_or_none()
    hole_res = await db.execute(
        select(CourseHole).where(
            CourseHole.course_id == round_.course_id,
            CourseHole.hole_number == hole_number,
        )
    )
    hole = hole_res.scalar_one_or_none()
    if hole and rp:
        from app.schemas.score import ScoreSubmit
        from app.services import scoring as scoring_svc
        data = ScoreSubmit(hole_number=hole_number, gross_score=correct_score)
        scoring_svc.apply_score_to_model(score, data, hole.par, hole.stroke_index or hole_number,
                                          rp.course_handicap or 0, round_.game_format, round_.max_handicap)
    else:
        score.gross_score = correct_score

    score.has_conflict = False
    score.conflict_score = None
    score.conflict_entered_by = None
    score.entered_by = current_user.id
    await db.flush()

    # Broadcast resolution
    await manager.broadcast_to_round(
        round_id=str(round_id),
        message={
            "event": "conflict_resolved",
            "user_id": str(uid),
            "hole": hole_number,
            "final_score": correct_score,
        },
    )

    return {"message": "Conflicto resuelto", "gross_score": correct_score, "has_conflict": False}


# ─── Live scoreboard (public, no auth) ───────────────────────────────────────

@router.get("/live/{invite_code}")
async def get_live_scoreboard(invite_code: str, db: DB):
    """Public real-time scoreboard — no authentication required."""
    result = await db.execute(select(Round).where(Round.invite_code == invite_code))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=404, detail="Jugada no encontrada")

    course_name = None
    if round_.course_id:
        cr = await db.execute(select(Course).where(Course.id == round_.course_id))
        c = cr.scalar_one_or_none()
        course_name = c.name if c else None

    players_result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_.id)
    )
    players_rows = players_result.all()

    from app.models.score import Score as ScoreModel
    scores_result = await db.execute(
        select(ScoreModel).where(ScoreModel.round_id == round_.id).order_by(ScoreModel.hole_number)
    )
    all_scores = scores_result.scalars().all()

    # Player totals
    player_totals: dict = {}
    for s in all_scores:
        uid = str(s.user_id)
        if uid not in player_totals:
            player_totals[uid] = {"gross": 0, "net": 0, "holes": 0, "stableford": 0}
        if s.gross_score:
            player_totals[uid]["gross"] += s.gross_score
            player_totals[uid]["net"] += (s.net_score or 0)
            player_totals[uid]["holes"] += 1
        if s.stableford_points:
            player_totals[uid]["stableford"] += s.stableford_points

    published = round_.teams_published
    has_teams = published and any(rp.team_number is not None for rp, _ in players_rows)

    # Build player list
    player_scores_list = []
    for rp, u in players_rows:
        uid = str(rp.user_id)
        t = player_totals.get(uid, {})
        player_scores_list.append({
            "user_id": uid,
            "name": f"{u.first_name} {u.last_name}",
            "username": u.username,
            "team_number": rp.team_number if published else None,
            "course_handicap": rp.course_handicap,
            "handicap_index": float(rp.handicap_index) if rp.handicap_index else None,
            "holes_played": t.get("holes", 0),
            "total_gross": t.get("gross", 0),
            "total_net": t.get("net", 0),
            "stableford": t.get("stableford", 0),
        })

    teams = []
    hole_results = []
    current_hole = max((s.hole_number for s in all_scores), default=0)

    if has_teams:
        teams_map: dict = {}
        for rp, u in players_rows:
            if rp.team_number is None:
                continue
            tn = rp.team_number
            if tn not in teams_map:
                teams_map[tn] = {
                    "team_number": tn, "name": f"Equipo {tn}",
                    "color": TEAM_COLORS[(tn - 1) % 4],
                    "players": [], "holes_won": 0, "holes_tied": 0,
                    "total_net": 0, "stableford": 0,
                    "_player_ids": set(),
                }
            uid = str(rp.user_id)
            t = player_totals.get(uid, {})
            teams_map[tn]["players"].append({
                "user_id": uid,
                "name": f"{u.first_name} {u.last_name}",
                "username": u.username,
                "course_handicap": rp.course_handicap,
                "handicap_index": float(rp.handicap_index) if rp.handicap_index else None,
                "holes_played": t.get("holes", 0),
                "total_gross": t.get("gross", 0),
                "total_net": t.get("net", 0),
                "stableford": t.get("stableford", 0),
            })
            teams_map[tn]["total_net"] += t.get("net", 0)
            teams_map[tn]["stableford"] += t.get("stableford", 0)
            teams_map[tn]["_player_ids"].add(uid)

        # Hole-by-hole team best net
        from collections import defaultdict
        hole_team_nets: dict = defaultdict(dict)
        for s in all_scores:
            uid = str(s.user_id)
            net = s.net_score if s.net_score is not None else s.gross_score
            if net is None:
                continue
            for tn, tdata in teams_map.items():
                if uid in tdata["_player_ids"]:
                    prev = hole_team_nets[s.hole_number].get(tn)
                    if prev is None or net < prev:
                        hole_team_nets[s.hole_number][tn] = net

        team_numbers = list(teams_map.keys())
        for h in range(1, round_.holes_to_play + 1):
            h_scores = hole_team_nets.get(h, {})
            if len(h_scores) < len(team_numbers):
                hole_results.append({"hole": h, "winner_team": None, "status": "pending", "team_scores": h_scores})
                continue
            min_net = min(h_scores.values())
            winners = [tn for tn, sc in h_scores.items() if sc == min_net]
            if len(winners) == 1:
                teams_map[winners[0]]["holes_won"] += 1
                hole_results.append({"hole": h, "winner_team": winners[0], "status": "won", "team_scores": h_scores})
            else:
                for tn in winners:
                    teams_map[tn]["holes_tied"] += 1
                hole_results.append({"hole": h, "winner_team": None, "status": "tied", "team_scores": h_scores})

        for tdata in teams_map.values():
            tdata.pop("_player_ids", None)
        teams = sorted(teams_map.values(), key=lambda t: -t["holes_won"])

    return {
        "round": {
            "id": str(round_.id),
            "name": round_.name,
            "course_name": course_name,
            "game_format": round_.game_format,
            "status": round_.status,
            "holes_to_play": round_.holes_to_play,
            "scheduled_at": round_.scheduled_at.isoformat(),
            "has_teams": has_teams,
        },
        "teams": teams,
        "hole_results": hole_results,
        "current_hole": current_hole,
        "player_scores": player_scores_list,
    }


# ─── Match scores (authenticated) ────────────────────────────────────────────

@router.get("/{round_id}/match-scores")
async def get_match_scores(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Hole-by-hole team match play results (requires published teams)."""
    round_result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=404, detail="Jugada no encontrada")

    if not round_.teams_published:
        return {"has_teams": False, "teams": [], "hole_results": []}

    players_result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id, RoundPlayer.team_number.isnot(None))
    )
    rows = players_result.all()
    if not rows:
        return {"has_teams": False, "teams": [], "hole_results": []}

    teams_map: dict = {}
    for rp, u in rows:
        tn = rp.team_number
        if tn not in teams_map:
            teams_map[tn] = {
                "team_number": tn, "name": f"Equipo {tn}",
                "color": TEAM_COLORS[(tn - 1) % 4],
                "holes_won": 0, "holes_tied": 0,
                "players": [], "_player_ids": set(),
            }
        teams_map[tn]["players"].append({
            "name": f"{u.first_name} {u.last_name}",
            "course_handicap": rp.course_handicap,
        })
        teams_map[tn]["_player_ids"].add(str(rp.user_id))

    from app.models.score import Score as ScoreModel
    scores_result = await db.execute(
        select(ScoreModel).where(ScoreModel.round_id == round_id).order_by(ScoreModel.hole_number)
    )
    all_scores = scores_result.scalars().all()

    from collections import defaultdict
    hole_team_nets: dict = defaultdict(dict)
    for s in all_scores:
        uid = str(s.user_id)
        net = s.net_score if s.net_score is not None else s.gross_score
        if net is None:
            continue
        for tn, tdata in teams_map.items():
            if uid in tdata["_player_ids"]:
                prev = hole_team_nets[s.hole_number].get(tn)
                if prev is None or net < prev:
                    hole_team_nets[s.hole_number][tn] = net

    team_numbers = list(teams_map.keys())
    hole_results = []
    for h in range(1, round_.holes_to_play + 1):
        h_scores = hole_team_nets.get(h, {})
        if len(h_scores) < len(team_numbers):
            hole_results.append({"hole": h, "winner_team": None, "status": "pending", "team_scores": h_scores})
            continue
        min_net = min(h_scores.values())
        winners = [tn for tn, sc in h_scores.items() if sc == min_net]
        if len(winners) == 1:
            teams_map[winners[0]]["holes_won"] += 1
            hole_results.append({"hole": h, "winner_team": winners[0], "status": "won", "team_scores": h_scores})
        else:
            for tn in winners:
                teams_map[tn]["holes_tied"] += 1
            hole_results.append({"hole": h, "winner_team": None, "status": "tied", "team_scores": h_scores})

    for tdata in teams_map.values():
        tdata.pop("_player_ids", None)

    return {
        "has_teams": True,
        "teams": sorted(teams_map.values(), key=lambda t: -t["holes_won"]),
        "hole_results": hole_results,
    }


@router.get("/{round_id}/florida-scores")
async def get_florida_scores(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Florida best-ball: team score = best net per hole. Lowest total net wins."""
    round_result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=404, detail="Jugada no encontrada")

    if not round_.teams_published:
        return {"has_teams": False, "teams": [], "hole_results": [], "holes_to_play": round_.holes_to_play}

    players_result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id, RoundPlayer.team_number.isnot(None))
    )
    rows = players_result.all()
    if not rows:
        return {"has_teams": False, "teams": [], "hole_results": [], "holes_to_play": round_.holes_to_play}

    teams_map: dict = {}
    for rp, u in rows:
        tn = rp.team_number
        if tn not in teams_map:
            teams_map[tn] = {
                "team_number": tn, "name": f"Equipo {tn}",
                "color": TEAM_COLORS[(tn - 1) % 4],
                "total_net": 0, "holes_completed": 0,
                "players": [], "_player_ids": set(),
            }
        teams_map[tn]["players"].append({
            "name": f"{u.first_name} {u.last_name}",
            "course_handicap": rp.course_handicap,
        })
        teams_map[tn]["_player_ids"].add(str(rp.user_id))

    from app.models.score import Score as ScoreModel
    from collections import defaultdict
    scores_result = await db.execute(
        select(ScoreModel).where(ScoreModel.round_id == round_id).order_by(ScoreModel.hole_number)
    )
    all_scores = scores_result.scalars().all()

    # Best net per team per hole
    hole_team_nets: dict = defaultdict(dict)
    for s in all_scores:
        uid = str(s.user_id)
        net = s.net_score if s.net_score is not None else s.gross_score
        if net is None:
            continue
        for tn, tdata in teams_map.items():
            if uid in tdata["_player_ids"]:
                prev = hole_team_nets[s.hole_number].get(tn)
                if prev is None or net < prev:
                    hole_team_nets[s.hole_number][tn] = net

    team_numbers = list(teams_map.keys())
    hole_results = []
    for h in range(1, round_.holes_to_play + 1):
        h_scores = hole_team_nets.get(h, {})
        if len(h_scores) < len(team_numbers):
            hole_results.append({"hole": h, "status": "pending", "winner_team": None, "team_scores": dict(h_scores)})
        else:
            min_net = min(h_scores.values())
            winners = [tn for tn, sc in h_scores.items() if sc == min_net]
            winner = winners[0] if len(winners) == 1 else None
            hole_results.append({
                "hole": h, "status": "won" if winner else "tied",
                "winner_team": winner, "team_scores": dict(h_scores),
            })

    # Sum best nets per team
    for tn in teams_map:
        total, completed = 0, 0
        for h in range(1, round_.holes_to_play + 1):
            if tn in hole_team_nets.get(h, {}):
                total += hole_team_nets[h][tn]
                completed += 1
        teams_map[tn]["total_net"] = total
        teams_map[tn]["holes_completed"] = completed
        teams_map[tn].pop("_player_ids", None)

    teams = sorted(teams_map.values(), key=lambda t: t["total_net"] if t["holes_completed"] > 0 else 9999)

    return {
        "has_teams": True,
        "teams": teams,
        "hole_results": hole_results,
        "holes_to_play": round_.holes_to_play,
    }


@router.get("/{round_id}/team-points")
async def get_team_points(round_id: uuid.UUID, db: DB):
    """Medal Play por equipos: puntos por posición NET dentro de cada grupo de salida.

    1°=+2, 2°=+1, último=-1 (siempre), resto=0. Empates por tarjeta (countback) en net.
    Suma por equipo → Campeón por Equipos. Público (sin auth), como el scoreboard en vivo.
    Requiere equipos publicados (teams_published) y grupos de salida (tee_group) asignados.
    """
    from app.services import team_points as tp_svc

    round_result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = round_result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=404, detail="Jugada no encontrada")

    if not round_.teams_published:
        return {"has_teams": False, "has_groups": False, "groups": [], "teams": [],
                "champion_team": None, "is_tie": False, "holes_to_play": round_.holes_to_play}

    players_result = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(RoundPlayer.round_id == round_id)
    )
    rows = players_result.all()

    scores_result = await db.execute(
        select(Score).where(Score.round_id == round_id).order_by(Score.hole_number)
    )
    all_scores = scores_result.scalars().all()

    # net por hoyo por jugador (cae a gross si no hay net calculado)
    per_hole: dict = {}
    for s in all_scores:
        uid = str(s.user_id)
        net = s.net_score if s.net_score is not None else s.gross_score
        if net is None:
            continue
        per_hole.setdefault(uid, {})[s.hole_number] = net

    players = []
    for rp, u in rows:
        # solo jugadores que realmente juegan (excluir retirados / no-playing)
        if rp.participant_mode != "playing" or rp.withdrawn_at is not None:
            continue
        uid = str(rp.user_id)
        hn = per_hole.get(uid, {})
        total_net = sum(hn.values()) if hn else None
        players.append({
            "user_id": uid,
            "name": f"{u.first_name} {u.last_name}",
            "team_number": rp.team_number,
            "tee_group": rp.tee_group,
            "starting_hole": rp.starting_hole,
            "course_handicap": rp.course_handicap,
            "per_hole_net": hn,
            "total_net": total_net,
            "holes_played": len(hn),
        })

    result = tp_svc.compute_team_points(players, round_.holes_to_play)
    # anotar color por equipo (mismo esquema que el resto del front)
    for t in result["teams"]:
        t["color"] = TEAM_COLORS[(t["team_number"] - 1) % 4]
    result["has_teams"] = any(p["team_number"] is not None for p in players)
    return result


# ─── Dev/Testing: Auto-fill scores ────────────────────────────────────────────

@router.post("/{round_id}/dev/fill-scores")
async def dev_fill_scores(round_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Genera scores aleatorios realistas para todos los jugadores activos.
    Solo creator. Borra los scores existentes antes de regenerar (idempotente).

    Distribución por hoyo (depende del C-HCP del jugador):
    - HCP bajo (≤9):  birdie 12% · par 45% · bogey 30% · doble 10% · otros 3%
    - HCP medio (10-18): birdie 6% · par 35% · bogey 40% · doble 15% · otros 4%
    - HCP alto (≥19): birdie 3% · par 25% · bogey 38% · doble 25% · otros 9%

    Solo para testing. NO usar en ronda real.
    """
    import random
    from app.models.score import Score as ScoreModel

    result = await db.execute(
        select(Round).where(Round.id == round_id, Round.created_by == current_user.id)
    )
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(status_code=403, detail="Solo el creador puede usar auto-fill")
    if round_.status not in ("active", "scheduled"):
        raise HTTPException(status_code=400, detail="La ronda debe estar en 'active' o 'scheduled' para auto-fill")

    # Hoyos del campo
    holes_res = await db.execute(
        select(CourseHole).where(CourseHole.course_id == round_.course_id).order_by(CourseHole.hole_number)
    )
    holes = holes_res.scalars().all()
    if not holes:
        raise HTTPException(status_code=400, detail="El campo no tiene hoyos configurados")
    holes_to_play = round_.holes_to_play
    target_holes = [h for h in holes if h.hole_number <= holes_to_play]

    # Jugadores activos (excluye withdrawn y observers)
    players_res = await db.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_id,
            RoundPlayer.status.in_(["confirmed", "playing", "finished"]),
            RoundPlayer.participant_mode == "playing",
        )
    )
    players = players_res.scalars().all()

    if not players:
        raise HTTPException(status_code=400, detail="No hay jugadores activos en la ronda")

    # Borrar scores existentes (idempotente)
    await db.execute(delete(ScoreModel).where(ScoreModel.round_id == round_id))
    await db.flush()

    # Si la ronda está en 'scheduled', moverla a 'active' para que el flujo siga
    if round_.status == "scheduled":
        from datetime import datetime, timezone
        round_.status = "active"
        round_.started_at = datetime.now(timezone.utc)

    def generate_gross(par: int, c_hcp: int) -> int:
        """Genera gross realista con sesgo según hándicap."""
        r = random.random()
        if c_hcp <= 9:
            # Buen jugador
            if r < 0.12: return max(1, par - 1)        # birdie
            elif r < 0.57: return par                   # par
            elif r < 0.87: return par + 1               # bogey
            elif r < 0.97: return par + 2               # doble
            else: return par + 3                        # triple+
        elif c_hcp <= 18:
            # Intermedio
            if r < 0.06: return max(1, par - 1)
            elif r < 0.41: return par
            elif r < 0.81: return par + 1
            elif r < 0.96: return par + 2
            else: return par + 3
        else:
            # Alto hándicap
            if r < 0.03: return max(1, par - 1)
            elif r < 0.28: return par
            elif r < 0.66: return par + 1
            elif r < 0.91: return par + 2
            else: return par + 3

    inserted = 0
    for p in players:
        c_hcp = p.course_handicap or 18
        for h in target_holes:
            par = h.par or 4
            si = h.stroke_index or h.hole_number
            gross = generate_gross(par, c_hcp)
            # Putts aproximados según resultado vs par
            diff = gross - par
            if diff < 0: putts = 1
            elif diff == 0: putts = 2
            elif diff == 1: putts = random.choice([2, 3])
            else: putts = random.choice([2, 3, 4])

            score = ScoreModel(
                round_id=round_id,
                user_id=p.user_id,
                hole_number=h.hole_number,
                entered_by=current_user.id,
            )
            db.add(score)
            # Reusar scoring_svc para que net/stableford/flags se calculen igual
            data = ScoreSubmit(hole_number=h.hole_number, gross_score=gross, putts=putts)
            scoring_svc.apply_score_to_model(score, data, par, si, c_hcp, round_.game_format, round_.max_handicap)
            inserted += 1

    await db.flush()

    await manager.broadcast_to_round(
        round_id=str(round_id),
        message={"event": "scores_autofilled", "round_id": str(round_id), "scores_inserted": inserted},
    )

    return {
        "message": "Scores generados",
        "round_id": str(round_id),
        "players": len(players),
        "holes_per_player": len(target_holes),
        "total_scores": inserted,
    }

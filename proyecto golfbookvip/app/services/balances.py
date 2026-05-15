"""Motor de cálculo de pérdidas y ganancias por jugador al cierre de la ronda.

Calcula balances finales tomando la configuración de apuestas y los scores
capturados. Solo considera jugadores que terminaron la ronda con scores válidos
(excluye withdrawn y observers).

Reglas implementadas (estándares de la mayoría de ligas):

- entry_fee:        Todos pagan. Pot = N × entry_fee. Distribución 60% / 30% / 10%
                    a los 3 mejores NET.
- nassau_front9:    Pot = N × nassau_front9. Ganador NET de los hoyos 1-9 toma el pot.
                    Empate = split entre los empatados.
- nassau_back9:     Igual que F9 pero para los hoyos 10-18.
- nassau_total:     Igual pero por los 18 hoyos completos.
- per_hole_bet:     Por cada hoyo, el ganador NET cobra per_hole_bet × (N-1) jugadores.
                    Empate = split entre los empatados.
- birdie_prize:     Cada birdie hecho → ese jugador cobra birdie_prize × (N-1).
- eagle_prize:      Igual para eagles.
- albatross_prize:  Igual para albatross.
- hole_in_one_prize: Igual para HIO.
- three_putt_penalty: Cada 3-putt → ese jugador paga penalty × (N-1) al pool de los demás.
- skins:            Hoyo a hoyo low score (gross o net según config) sin empate = skin.
                    Empate = carry-over al siguiente. Skin acumulado = skins_value × (N-1).
                    Skins sin ganar al final → forfeit (se pierden).
- oyes:             Por ahora $0 (regla regional pendiente de definir).
"""

from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.round import Round, RoundPlayer, RoundBetConfig
from app.models.score import Score
from app.models.course import CourseHole
from app.models.user import User


def _split(amount: float, n: int) -> float:
    """División segura."""
    return amount / n if n > 0 else 0.0


async def compute_balances(round_id: str, db: AsyncSession) -> dict[str, Any]:
    """Calcula balance final por jugador de una ronda."""
    # 1. Cargar ronda
    r_res = await db.execute(select(Round).where(Round.id == round_id))
    round_ = r_res.scalar_one_or_none()
    if not round_:
        return {"error": "round_not_found"}

    # 2. Cargar bet config
    bc_res = await db.execute(select(RoundBetConfig).where(RoundBetConfig.round_id == round_id))
    bc = bc_res.scalar_one_or_none()
    if not bc:
        return {"has_bets": False, "players": [], "lines": []}

    # 3. Cargar jugadores activos (no withdrawn, no observer)
    p_res = await db.execute(
        select(RoundPlayer, User)
        .join(User, User.id == RoundPlayer.user_id)
        .where(
            RoundPlayer.round_id == round_id,
            RoundPlayer.status.in_(["confirmed", "playing", "finished"]),
            RoundPlayer.participant_mode == "playing",
            RoundPlayer.in_bet == True,
            RoundPlayer.withdrawn_at.is_(None),
        )
    )
    rows = p_res.all()
    players = [{"user_id": str(p.user_id), "rp": p, "name": f"{u.first_name} {u.last_name}"} for p, u in rows]
    n = len(players)
    if n < 2:
        return {"has_bets": False, "players": [], "lines": [], "note": "Se requieren al menos 2 jugadores para calcular apuestas"}

    # 4. Cargar todos los scores
    s_res = await db.execute(
        select(Score).where(Score.round_id == round_id)
    )
    all_scores = s_res.scalars().all()
    # scores_by[user_id][hole] = (gross, net)
    scores_by: dict[str, dict[int, dict[str, Any]]] = {}
    for s in all_scores:
        uid = str(s.user_id)
        scores_by.setdefault(uid, {})[s.hole_number] = {
            "gross": s.gross_score or 0,
            "net": s.net_score or 0,
            "is_birdie": s.is_birdie,
            "is_eagle": s.is_eagle,
            "is_albatross": s.is_albatross,
            "is_hole_in_one": s.is_hole_in_one,
            "is_three_putt": s.is_three_putt,
        }

    # 5. Cargar pars del curso
    h_res = await db.execute(
        select(CourseHole).where(CourseHole.course_id == round_.course_id).order_by(CourseHole.hole_number)
    )
    holes = h_res.scalars().all()
    par_by_hole = {h.hole_number: (h.par or 0) for h in holes}

    holes_played = round_.holes_to_play

    # Inicializar buckets de balance por jugador
    bal: dict[str, dict[str, float]] = {
        p["user_id"]: {
            "entry_fee": 0.0,
            "nassau": 0.0,
            "per_hole": 0.0,
            "prizes": 0.0,
            "penalties": 0.0,
            "skins": 0.0,
            "oyes": 0.0,
            "total": 0.0,
        }
        for p in players
    }

    lines: list[dict[str, Any]] = []

    def add_line(kind: str, detail: str, amounts: dict[str, float]):
        """Registra línea explicativa con desglose por jugador."""
        lines.append({"kind": kind, "detail": detail, "amounts": amounts})

    # ─── ENTRY FEE: 60/30/10 al low net total ─────────────────────────────────
    if bc.entry_fee and float(bc.entry_fee) > 0:
        fee = float(bc.entry_fee)
        pot = fee * n
        # Cada jugador paga la entrada
        for p in players:
            bal[p["user_id"]]["entry_fee"] -= fee
        # Ordenar por low net total
        net_totals = []
        for p in players:
            uid = p["user_id"]
            ps = scores_by.get(uid, {})
            total_net = sum(ps[h]["net"] for h in range(1, holes_played + 1) if h in ps)
            holes_with_score = sum(1 for h in range(1, holes_played + 1) if h in ps)
            if holes_with_score == holes_played:
                net_totals.append((uid, total_net))
        net_totals.sort(key=lambda x: x[1])
        # Distribución 60/30/10
        shares = [0.60, 0.30, 0.10]
        amounts_paid: dict[str, float] = {p["user_id"]: -fee for p in players}
        for i, share in enumerate(shares):
            if i < len(net_totals):
                winner_uid = net_totals[i][0]
                prize = pot * share
                bal[winner_uid]["entry_fee"] += prize
                amounts_paid[winner_uid] = amounts_paid.get(winner_uid, 0) + prize
        add_line("entry_fee", f"Entry fee ${fee}: pot ${pot:.2f} dividido 60/30/10 a low net", amounts_paid)

    # ─── NASSAU F9 / B9 / Total ───────────────────────────────────────────────
    if bc.nassau_enabled:
        def nassau_segment(label: str, hole_range: range, amount: float):
            if not amount or amount <= 0:
                return
            pot = amount * n
            # Cada jugador paga
            for p in players:
                bal[p["user_id"]]["nassau"] -= amount
            # Encontrar low net del segmento (solo jugadores que terminaron el segmento)
            segment_totals = []
            for p in players:
                uid = p["user_id"]
                ps = scores_by.get(uid, {})
                holes_in_seg = [h for h in hole_range if h in ps]
                if len(holes_in_seg) == len(hole_range):
                    seg_net = sum(ps[h]["net"] for h in holes_in_seg)
                    segment_totals.append((uid, seg_net))
            if not segment_totals:
                return
            min_net = min(s[1] for s in segment_totals)
            winners = [uid for uid, n2 in segment_totals if n2 == min_net]
            prize_each = pot / len(winners)
            amounts_paid: dict[str, float] = {p["user_id"]: -amount for p in players}
            for w in winners:
                bal[w]["nassau"] += prize_each
                amounts_paid[w] = amounts_paid.get(w, 0) + prize_each
            label_full = f"Nassau {label} ${amount}: pot ${pot:.2f} → ganador(es) net {min_net}"
            add_line("nassau", label_full, amounts_paid)

        if holes_played >= 9:
            nassau_segment("Salida (1-9)", range(1, 10), float(bc.nassau_front9))
        if holes_played >= 18:
            nassau_segment("Vuelta (10-18)", range(10, 19), float(bc.nassau_back9))
            nassau_segment("Total (1-18)", range(1, 19), float(bc.nassau_total))

    # ─── PER HOLE BET — low net por hoyo ──────────────────────────────────────
    if bc.per_hole_bet and float(bc.per_hole_bet) > 0:
        per_hole = float(bc.per_hole_bet)
        total_per_hole: dict[str, float] = {p["user_id"]: 0.0 for p in players}
        for h in range(1, holes_played + 1):
            # Recolectar nets del hoyo
            hole_nets = []
            for p in players:
                uid = p["user_id"]
                ps = scores_by.get(uid, {})
                if h in ps:
                    hole_nets.append((uid, ps[h]["net"]))
            if len(hole_nets) < 2:
                continue
            min_net = min(n2 for _, n2 in hole_nets)
            winners = [uid for uid, n2 in hole_nets if n2 == min_net]
            losers = [uid for uid, n2 in hole_nets if n2 > min_net]
            if not losers:
                continue  # todos empatados → no se mueve dinero
            # Cada loser paga per_hole_bet, total se divide entre winners
            pot = per_hole * len(losers)
            prize_each = pot / len(winners)
            for l in losers:
                total_per_hole[l] -= per_hole
            for w in winners:
                total_per_hole[w] = total_per_hole.get(w, 0) + prize_each
        if any(abs(v) > 0.01 for v in total_per_hole.values()):
            for uid, amt in total_per_hole.items():
                bal[uid]["per_hole"] += amt
            add_line("per_hole", f"Por hoyo ganado ${per_hole}: low net por hoyo cobra a los que pierden", total_per_hole)

    # ─── PRIZES: Birdie / Eagle / Albatross / HIO (pay-each-other) ────────────
    def prize_event(label: str, flag: str, prize_amount: float):
        if not prize_amount or prize_amount <= 0:
            return
        amount = float(prize_amount)
        total_prize: dict[str, float] = {p["user_id"]: 0.0 for p in players}
        for p in players:
            uid = p["user_id"]
            ps = scores_by.get(uid, {})
            count = sum(1 for h in range(1, holes_played + 1) if h in ps and ps[h].get(flag))
            if count > 0:
                # Cada birdie: este jugador cobra `amount` de cada uno de los otros (N-1) jugadores
                # = +amount × (N-1) para él, y -amount para cada otro, por cada birdie
                gain_per_event = amount * (n - 1)
                total_prize[uid] += gain_per_event * count
                for other in players:
                    if other["user_id"] != uid:
                        total_prize[other["user_id"]] -= amount * count
        if any(abs(v) > 0.01 for v in total_prize.values()):
            for uid, amt in total_prize.items():
                bal[uid]["prizes"] += amt
            add_line("prize", f"{label} ${amount}: cada uno paga al que lo hizo", total_prize)

    prize_event("Birdies", "is_birdie", float(bc.birdie_prize))
    prize_event("Eagles", "is_eagle", float(bc.eagle_prize))
    prize_event("Albatross", "is_albatross", float(bc.albatross_prize or 0))
    prize_event("Hoyo en uno", "is_hole_in_one", float(bc.hole_in_one_prize))

    # ─── 3-PUTT PENALTY (pay-each-other reverso) ──────────────────────────────
    if bc.three_putt_penalty and float(bc.three_putt_penalty) > 0:
        penalty = float(bc.three_putt_penalty)
        total_pen: dict[str, float] = {p["user_id"]: 0.0 for p in players}
        for p in players:
            uid = p["user_id"]
            ps = scores_by.get(uid, {})
            count = sum(1 for h in range(1, holes_played + 1) if h in ps and ps[h].get("is_three_putt"))
            if count > 0:
                # El penalizado paga `penalty` a cada otro jugador, por cada 3-putt
                total_pen[uid] -= penalty * (n - 1) * count
                for other in players:
                    if other["user_id"] != uid:
                        total_pen[other["user_id"]] += penalty * count
        if any(abs(v) > 0.01 for v in total_pen.values()):
            for uid, amt in total_pen.items():
                bal[uid]["penalties"] += amt
            add_line("penalty", f"Penalidad 3 putts ${penalty}: paga al resto cada 3-putt", total_pen)

    # ─── SKINS con carry-over ─────────────────────────────────────────────────
    if bc.skins_enabled and bc.skins_value and float(bc.skins_value) > 0:
        skin_val = float(bc.skins_value)
        use_net = bool(bc.skins_use_net)
        carry = 1  # carry start = 1 (cada hoyo vale 1 skin base)
        skins_won: dict[str, int] = {p["user_id"]: 0 for p in players}
        for h in range(1, holes_played + 1):
            scores_h = []
            for p in players:
                uid = p["user_id"]
                ps = scores_by.get(uid, {})
                if h in ps:
                    s_val = ps[h]["net"] if use_net else ps[h]["gross"]
                    scores_h.append((uid, s_val))
            if len(scores_h) < 2:
                continue
            min_s = min(s for _, s in scores_h)
            winners = [uid for uid, s in scores_h if s == min_s]
            if len(winners) == 1:
                skins_won[winners[0]] += carry
                carry = 1
            else:
                # empate → carry-over
                carry += 1

        if any(skins_won.values()):
            total_skins: dict[str, float] = {p["user_id"]: 0.0 for p in players}
            # Cada skin ganado vale skins_value × (N-1) para el ganador,
            # y costa skins_value a cada otro jugador
            for winner_uid, count in skins_won.items():
                if count > 0:
                    total_skins[winner_uid] += skin_val * (n - 1) * count
                    for other in players:
                        if other["user_id"] != winner_uid:
                            total_skins[other["user_id"]] -= skin_val * count
            for uid, amt in total_skins.items():
                bal[uid]["skins"] += amt
            kind_label = "net" if use_net else "gross"
            add_line("skins", f"Skines ${skin_val} ({kind_label}, carry en empate): cada skin paga ${skin_val} de cada otro", total_skins)

    # ─── Sumar totales ────────────────────────────────────────────────────────
    for uid in bal:
        bal[uid]["total"] = (
            bal[uid]["entry_fee"]
            + bal[uid]["nassau"]
            + bal[uid]["per_hole"]
            + bal[uid]["prizes"]
            + bal[uid]["penalties"]
            + bal[uid]["skins"]
            + bal[uid]["oyes"]
        )

    # Devolver lista ordenada por total desc (ganadores arriba)
    players_out = sorted(
        [
            {
                "user_id": p["user_id"],
                "name": p["name"],
                "course_handicap": p["rp"].course_handicap,
                "breakdown": bal[p["user_id"]],
            }
            for p in players
        ],
        key=lambda x: -x["breakdown"]["total"],
    )

    return {
        "has_bets": True,
        "players": players_out,
        "lines": lines,
        "summary": {
            "total_players": n,
            "total_entry_fee": float(bc.entry_fee) * n,
            "skins_value": float(bc.skins_value) if bc.skins_enabled else 0,
        },
    }

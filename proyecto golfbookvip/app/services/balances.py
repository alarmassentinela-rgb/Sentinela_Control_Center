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

import logging
from decimal import Decimal, ROUND_DOWN
from typing import Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.round import Round, RoundPlayer, RoundBetConfig
from app.models.score import Score, RoundPlayerBalance
from app.models.course import CourseHole
from app.models.user import User


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def _money(value) -> Decimal:
    return Decimal(str(value or 0))


def _cents(value: Decimal) -> Decimal:
    return value.quantize(CENT)


def _allocate(amount: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Reparte en centavos y asigna residuos por largest remainder para que la suma cierre exacta."""
    if not weights:
        return []
    total_weight = sum(weights, ZERO)
    if total_weight <= 0:
        return [ZERO for _ in weights]
    amount = _cents(amount)
    ideals = [(amount * weight / total_weight) for weight in weights]
    floors = [ideal.quantize(CENT, rounding=ROUND_DOWN) for ideal in ideals]
    residual_cents = int(((amount - sum(floors, ZERO)) / CENT).to_integral_value())
    remainders = sorted(
        range(len(weights)),
        key=lambda idx: (ideals[idx] - floors[idx], -idx),
        reverse=True,
    )
    for idx in remainders[:residual_cents]:
        floors[idx] += CENT
    return floors


def _split(amount: Decimal, n: int) -> list[Decimal]:
    """División segura en centavos; el residuo queda en el primer ganador por largest remainder."""
    return _allocate(amount, [Decimal("1") for _ in range(n)]) if n > 0 else []


def _txt(lang: str, es: str, en: str) -> str:
    """Helper bilingüe — devuelve el string según el idioma."""
    return en if lang == "en" else es


async def compute_balances(round_id: str, db: AsyncSession, lang: str = "es") -> dict[str, Any]:
    """Calcula balance final por jugador de una ronda.

    Args:
        round_id: UUID de la ronda
        db: sesión async
        lang: 'es' (default) o 'en' — idioma de los strings descriptivos en 'lines[].detail'
    """
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
        return {"has_bets": False, "players": [], "lines": [],
                "note": _txt(lang,
                    "Se requieren al menos 2 jugadores para calcular apuestas",
                    "At least 2 players are required to calculate bets")}

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
    bal: dict[str, dict[str, Decimal]] = {
        p["user_id"]: {
            "entry_fee": ZERO,
            "nassau": ZERO,
            "per_hole": ZERO,
            "prizes": ZERO,
            "penalties": ZERO,
            "skins": ZERO,
            "oyes": ZERO,
            "total": ZERO,
        }
        for p in players
    }
    total_forfeited = ZERO

    lines: list[dict[str, Any]] = []

    def add_line(kind: str, detail: str, amounts: dict[str, Decimal], breakdown: str | None = None):
        """Registra línea explicativa con desglose por jugador.
        breakdown: texto multilínea opcional con explicación detallada (hoyos, nets, fórmula)
                   que el frontend muestra en modal al click "Detalle"."""
        entry = {"kind": kind, "detail": detail, "amounts": amounts}
        if breakdown:
            entry["breakdown"] = breakdown
        lines.append(entry)

    def _name_of(uid: str) -> str:
        for pp in players:
            if pp["user_id"] == uid:
                return pp["name"]
        return uid[:8]

    # ─── ENTRY FEE: 60/30/10 al low net total ─────────────────────────────────
    if bc.entry_fee and _money(bc.entry_fee) > 0:
        fee = _cents(_money(bc.entry_fee))
        pot = _cents(fee * n)
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
        shares = [Decimal("0.60"), Decimal("0.30"), Decimal("0.10")]
        share_labels_es = ["1° lugar", "2° lugar", "3° lugar"]
        share_labels_en = ["1st place", "2nd place", "3rd place"]
        amounts_paid: dict[str, Decimal] = {p["user_id"]: -fee for p in players}
        winners_info: list[tuple[int, str, Decimal, int]] = []  # (idx, name, prize, net)
        active_shares = shares[:min(len(shares), len(net_totals))]
        prizes = _allocate(pot, active_shares)
        for i, prize in enumerate(prizes):
            if i < len(net_totals):
                winner_uid = net_totals[i][0]
                bal[winner_uid]["entry_fee"] += prize
                amounts_paid[winner_uid] = amounts_paid.get(winner_uid, ZERO) + prize
                winners_info.append((i, _name_of(winner_uid), prize, net_totals[i][1]))
        # Construir breakdown
        bd_lines = []
        if lang == "en":
            bd_lines.append(f"Entry fee: ${fee:.2f} per player × {n} players = pot ${pot:.2f}")
            bd_lines.append(f"Distribution 60% / 30% / 10% to lowest net total ({holes_played} holes):")
            for idx, name, prize, net_val in winners_info:
                pct = int(shares[idx] * 100)
                bd_lines.append(f"  {share_labels_en[idx]}: {name} (net {net_val}) → ${prize:.2f} ({pct}% of pot)")
            bd_lines.append("")
            bd_lines.append(f"Every player paid ${fee:.2f} to enter; winners receive their share back plus the prize.")
        else:
            bd_lines.append(f"Entry fee: ${fee:.2f} por jugador × {n} jugadores = pot ${pot:.2f}")
            bd_lines.append(f"Distribución 60% / 30% / 10% al low net total ({holes_played} hoyos):")
            for idx, name, prize, net_val in winners_info:
                pct = int(shares[idx] * 100)
                bd_lines.append(f"  {share_labels_es[idx]}: {name} (net {net_val}) → ${prize:.2f} ({pct}% del pot)")
            bd_lines.append("")
            bd_lines.append(f"Cada jugador pagó ${fee:.2f} de entrada; los ganadores reciben su aporte de regreso más el premio.")
        add_line("entry_fee",
            _txt(lang,
                f"Entry fee ${fee}: pot ${pot:.2f} dividido 60/30/10 a low net",
                f"Entry fee ${fee}: pot ${pot:.2f} split 60/30/10 to low net"),
            amounts_paid,
            breakdown="\n".join(bd_lines))

    # ─── NASSAU F9 / B9 / Total ───────────────────────────────────────────────
    if bc.nassau_enabled:
        def nassau_segment(label: str, hole_range: range, amount: Decimal):
            if not amount or amount <= 0:
                return
            amount = _cents(amount)
            pot = _cents(amount * n)
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
            prizes = _split(pot, len(winners))
            prize_each = prizes[0] if prizes else ZERO
            amounts_paid: dict[str, Decimal] = {p["user_id"]: -amount for p in players}
            for idx, w in enumerate(winners):
                prize = prizes[idx]
                bal[w]["nassau"] += prize
                amounts_paid[w] = amounts_paid.get(w, ZERO) + prize
            label_full = _txt(lang,
                f"Nassau {label} ${amount}: pot ${pot:.2f} → ganador(es) net {min_net}",
                f"Nassau {label} ${amount}: pot ${pot:.2f} → winner(s) net {min_net}")
            # Breakdown — todos los nets del segmento + ganadores + fórmula
            sorted_nets = sorted(segment_totals, key=lambda x: x[1])
            bd_lines = []
            if lang == "en":
                bd_lines.append(f"Nassau {label}: ${amount:.2f} per player × {n} players = pot ${pot:.2f}")
                bd_lines.append(f"Each player paid ${amount:.2f}. Winner takes the full pot.")
                bd_lines.append(f"Net total per player in this segment:")
                for uid, net_val in sorted_nets:
                    mark = " ← WINNER" if uid in winners else ""
                    bd_lines.append(f"  {_name_of(uid)}: {net_val}{mark}")
                bd_lines.append("")
                if len(winners) == 1:
                    bd_lines.append(f"{_name_of(winners[0])} (net {min_net}) wins the pot: ${pot:.2f}")
                else:
                    bd_lines.append(f"{len(winners)} players tied at net {min_net} → pot split = ${prize_each:.2f} each")
            else:
                bd_lines.append(f"Nassau {label}: ${amount:.2f} por jugador × {n} jugadores = pot ${pot:.2f}")
                bd_lines.append(f"Cada jugador pagó ${amount:.2f}. El ganador se lleva el pot completo.")
                bd_lines.append(f"Net total por jugador en este segmento:")
                for uid, net_val in sorted_nets:
                    mark = " ← GANADOR" if uid in winners else ""
                    bd_lines.append(f"  {_name_of(uid)}: {net_val}{mark}")
                bd_lines.append("")
                if len(winners) == 1:
                    bd_lines.append(f"{_name_of(winners[0])} (net {min_net}) gana el pot: ${pot:.2f}")
                else:
                    bd_lines.append(f"{len(winners)} jugadores empatados en net {min_net} → pot dividido = ${prize_each:.2f} c/u")
            add_line("nassau", label_full, amounts_paid, breakdown="\n".join(bd_lines))

        if holes_played >= 9:
            nassau_segment(_txt(lang, "Salida (1-9)", "Front 9 (1-9)"), range(1, 10), _money(bc.nassau_front9))
        if holes_played >= 18:
            nassau_segment(_txt(lang, "Vuelta (10-18)", "Back 9 (10-18)"), range(10, 19), _money(bc.nassau_back9))
            nassau_segment(_txt(lang, "Total (1-18)", "Total (1-18)"), range(1, 19), _money(bc.nassau_total))

    # ─── PER HOLE BET — low net por hoyo ──────────────────────────────────────
    if bc.per_hole_bet and _money(bc.per_hole_bet) > 0:
        per_hole = _cents(_money(bc.per_hole_bet))
        total_per_hole: dict[str, Decimal] = {p["user_id"]: ZERO for p in players}
        hole_results: list[tuple[int, list[str], list[str], int]] = []  # (hole, winner_uids, loser_uids, min_net)
        for h in range(1, holes_played + 1):
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
                continue
            pot = _cents(per_hole * len(losers))
            prizes = _split(pot, len(winners))
            prize_each = prizes[0] if prizes else ZERO
            for l in losers:
                total_per_hole[l] -= per_hole
            for idx, w in enumerate(winners):
                total_per_hole[w] = total_per_hole.get(w, ZERO) + prizes[idx]
            hole_results.append((h, winners, losers, min_net))
        if any(abs(v) > CENT for v in total_per_hole.values()):
            for uid, amt in total_per_hole.items():
                bal[uid]["per_hole"] += amt
            # Breakdown hoyo por hoyo
            bd_lines = []
            if lang == "en":
                bd_lines.append(f"Per hole bet: ${per_hole:.2f}. Lowest net per hole wins ${per_hole:.2f} from each loser.")
                bd_lines.append(f"Tied holes don't move money.")
                bd_lines.append("")
                bd_lines.append("Hole by hole (only holes with money movement):")
                for h, winners, losers, min_net in hole_results:
                    wnames = ", ".join(_name_of(w) for w in winners)
                    pot_h = _cents(per_hole * len(losers))
                    prize = (_split(pot_h, len(winners))[0] if winners else ZERO)
                    bd_lines.append(f"  Hole {h} (net {min_net}): {wnames} +${prize:.2f}  ·  {len(losers)} loser{'s' if len(losers) != 1 else ''} −${per_hole:.2f}")
            else:
                bd_lines.append(f"Apuesta por hoyo: ${per_hole:.2f}. El low net de cada hoyo cobra ${per_hole:.2f} a cada perdedor.")
                bd_lines.append(f"Hoyos empatados no mueven dinero.")
                bd_lines.append("")
                bd_lines.append("Hoyo por hoyo (solo hoyos con movimiento):")
                for h, winners, losers, min_net in hole_results:
                    wnames = ", ".join(_name_of(w) for w in winners)
                    pot_h = _cents(per_hole * len(losers))
                    prize = (_split(pot_h, len(winners))[0] if winners else ZERO)
                    plural_l = "es" if len(losers) != 1 else ""
                    bd_lines.append(f"  Hoyo {h} (net {min_net}): {wnames} +${prize:.2f}  ·  {len(losers)} perdedor{plural_l} −${per_hole:.2f}")
            add_line("per_hole",
                _txt(lang,
                    f"Por hoyo ganado ${per_hole}: low net por hoyo cobra a los que pierden",
                    f"Per hole won ${per_hole}: low net per hole charges losers"),
                total_per_hole,
                breakdown="\n".join(bd_lines))

    # ─── PRIZES: Birdie / Eagle / Albatross / HIO (pay-each-other) ────────────
    # Genera UNA línea por (jugador, tipo de evento) para que el desglose muestre
    # exactamente cuántos hizo cada uno.
    def prize_event(label_es: str, label_en: str, flag: str, prize_amount: Decimal):
        if not prize_amount or prize_amount <= 0:
            return
        amount = _cents(prize_amount)
        # Contar eventos por jugador
        events_by_player: list[tuple[str, str, int]] = []  # (uid, name, count)
        for p in players:
            uid = p["user_id"]
            ps = scores_by.get(uid, {})
            count = sum(1 for h in range(1, holes_played + 1) if h in ps and ps[h].get(flag))
            if count > 0:
                events_by_player.append((uid, p["name"], count))
        if not events_by_player:
            return
        # Por cada jugador con eventos, agregar línea individual
        for uid, name, count in events_by_player:
            gain = _cents(amount * (n - 1) * count)
            line_amounts: dict[str, Decimal] = {p["user_id"]: ZERO for p in players}
            line_amounts[uid] = gain
            for other in players:
                if other["user_id"] != uid:
                    line_amounts[other["user_id"]] = -_cents(amount * count)
            bal[uid]["prizes"] += gain
            for other in players:
                if other["user_id"] != uid:
                    bal[other["user_id"]]["prizes"] -= _cents(amount * count)
            plural = "s" if count > 1 else ""
            # Listar los hoyos donde el jugador hizo el evento
            ps = scores_by.get(uid, {})
            holes_with_event = [h for h in range(1, holes_played + 1) if h in ps and ps[h].get(flag)]
            if lang == "en":
                detail = f"{name} made {count} {label_en.lower()}{plural} (${amount:.0f} each) → earns ${amount:.0f} × {n - 1} others × {count} = ${gain:.2f}"
                bd_lines = [
                    f"{label_en} prize: ${amount:.2f} per event.",
                    f"{name} achieved {count} {label_en.lower()}{plural} on hole{'s' if count != 1 else ''}: {', '.join(str(h) for h in holes_with_event)}.",
                    f"Each of the other {n - 1} players pays ${amount:.2f} per event.",
                    f"Total: ${amount:.2f} × {n - 1} other players × {count} event{plural} = ${gain:.2f}",
                ]
            else:
                detail = f"{name} hizo {count} {label_es.lower()}{plural} (${amount:.0f} c/u) → cobra ${amount:.0f} × {n - 1} otros × {count} = ${gain:.2f}"
                plural_h = "s" if count != 1 else ""
                bd_lines = [
                    f"Premio {label_es}: ${amount:.2f} por evento.",
                    f"{name} logró {count} {label_es.lower()}{plural} en el hoyo{plural_h}: {', '.join(str(h) for h in holes_with_event)}.",
                    f"Cada uno de los otros {n - 1} jugadores paga ${amount:.2f} por evento.",
                    f"Total: ${amount:.2f} × {n - 1} otros jugadores × {count} evento{plural} = ${gain:.2f}",
                ]
            add_line("prize", detail, line_amounts, breakdown="\n".join(bd_lines))

    prize_event("Birdie", "Birdies", "is_birdie", _money(bc.birdie_prize))
    prize_event("Eagle", "Eagles", "is_eagle", _money(bc.eagle_prize))
    prize_event("Albatross", "Albatross", "is_albatross", _money(bc.albatross_prize))
    prize_event("Hoyo en uno", "Holes in one", "is_hole_in_one", _money(bc.hole_in_one_prize))

    # ─── 3-PUTT PENALTY (pay-each-other reverso) ──────────────────────────────
    if bc.three_putt_penalty and _money(bc.three_putt_penalty) > 0:
        penalty = _cents(_money(bc.three_putt_penalty))
        total_pen: dict[str, Decimal] = {p["user_id"]: ZERO for p in players}
        three_putt_events: list[tuple[str, list[int]]] = []  # (uid, holes_list)
        for p in players:
            uid = p["user_id"]
            ps = scores_by.get(uid, {})
            holes_3p = [h for h in range(1, holes_played + 1) if h in ps and ps[h].get("is_three_putt")]
            count = len(holes_3p)
            if count > 0:
                three_putt_events.append((uid, holes_3p))
                total_pen[uid] -= _cents(penalty * (n - 1) * count)
                for other in players:
                    if other["user_id"] != uid:
                        total_pen[other["user_id"]] += _cents(penalty * count)
        if any(abs(v) > CENT for v in total_pen.values()):
            for uid, amt in total_pen.items():
                bal[uid]["penalties"] += amt
            # Breakdown — listar cada penalizado con sus hoyos
            bd_lines = []
            if lang == "en":
                bd_lines.append(f"3-putt penalty: ${penalty:.2f} per 3-putt. The 3-putter pays each other player ${penalty:.2f}.")
                bd_lines.append("")
                for uid, holes_3p in three_putt_events:
                    holes_str = ", ".join(str(h) for h in holes_3p)
                    paid = _cents(penalty * (n - 1) * len(holes_3p))
                    bd_lines.append(f"  {_name_of(uid)}: {len(holes_3p)} 3-putt{'s' if len(holes_3p) != 1 else ''} on hole{'s' if len(holes_3p) != 1 else ''} {holes_str} → pays ${paid:.2f}")
            else:
                bd_lines.append(f"Penalidad 3-putt: ${penalty:.2f} por cada 3-putt. El que hizo 3-putt paga ${penalty:.2f} a cada otro jugador.")
                bd_lines.append("")
                for uid, holes_3p in three_putt_events:
                    holes_str = ", ".join(str(h) for h in holes_3p)
                    paid = _cents(penalty * (n - 1) * len(holes_3p))
                    plural_h = "es" if len(holes_3p) != 1 else ""
                    plural_p = "s" if len(holes_3p) != 1 else ""
                    bd_lines.append(f"  {_name_of(uid)}: {len(holes_3p)} 3-putt{plural_p} en hoyo{plural_h} {holes_str} → paga ${paid:.2f}")
            add_line("penalty",
                _txt(lang,
                    f"Penalidad 3 putts ${penalty}: paga al resto cada 3-putt",
                    f"3-putt penalty ${penalty}: pays the rest for each 3-putt"),
                total_pen,
                breakdown="\n".join(bd_lines))

    # ─── SKINS con carry-over (detalle hoyo por hoyo) ─────────────────────────
    if bc.skins_enabled and bc.skins_value and _money(bc.skins_value) > 0:
        skin_val = _cents(_money(bc.skins_value))
        use_net = bool(bc.skins_use_net)
        kind_label = "net" if use_net else "gross"
        carry = 1
        carry_holes: list[int] = []
        # Tracks: cada evento ganado → (winner_uid, hole, skins_won, carry_from_holes)
        won_events: list[tuple[str, int, int, list[int]]] = []

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
                won_events.append((winners[0], h, carry, list(carry_holes)))
                carry_holes = []
                carry = 1
            else:
                carry_holes.append(h)
                carry += 1

        forfeit_holes = carry_holes
        forfeit_skins = carry - 1 if forfeit_holes else 0

        # Generar una línea por evento ganado
        for winner_uid, hole, skins_won_count, carry_from in won_events:
            winner_name = next((p["name"] for p in players if p["user_id"] == winner_uid), winner_uid)
            gain = _cents(skin_val * (n - 1) * skins_won_count)
            line_amounts: dict[str, Decimal] = {p["user_id"]: ZERO for p in players}
            line_amounts[winner_uid] = gain
            for other in players:
                if other["user_id"] != winner_uid:
                    line_amounts[other["user_id"]] = -_cents(skin_val * skins_won_count)
            bal[winner_uid]["skins"] += gain
            for other in players:
                if other["user_id"] != winner_uid:
                    bal[other["user_id"]]["skins"] -= _cents(skin_val * skins_won_count)

            if carry_from:
                holes_str = ", ".join(f"H{h}" for h in carry_from)
                if lang == "en":
                    detail = (
                        f"Hole {hole}: {winner_name} outright low {kind_label} → "
                        f"+{skins_won_count} accumulated skins (carry from {holes_str}) = ${gain:.2f}"
                    )
                else:
                    detail = (
                        f"Hoyo {hole}: {winner_name} low {kind_label} outright → "
                        f"+{skins_won_count} skins acumulados (carry desde {holes_str}) = ${gain:.2f}"
                    )
            else:
                if lang == "en":
                    detail = f"Hole {hole}: {winner_name} outright low {kind_label} → +1 skin = ${gain:.2f}"
                else:
                    detail = f"Hoyo {hole}: {winner_name} low {kind_label} outright → +1 skin = ${gain:.2f}"
            # Breakdown — explicar fórmula y reparto
            if lang == "en":
                bd_lines = [
                    f"Skins value: ${skin_val:.2f} per skin. Mode: {kind_label} score.",
                    f"Hole {hole}: {winner_name} had the lowest {kind_label} score (no tie).",
                ]
                if carry_from:
                    bd_lines.append(f"Carry from hole{'s' if len(carry_from) != 1 else ''} {', '.join(str(h) for h in carry_from)} (tied → carried over).")
                    bd_lines.append(f"Total skins won on hole {hole}: {skins_won_count} (1 from this hole + {len(carry_from)} carry).")
                else:
                    bd_lines.append(f"No carry — won 1 skin.")
                bd_lines.append("")
                bd_lines.append(f"Each of the other {n - 1} players pays ${skin_val:.2f} × {skins_won_count} skin{'s' if skins_won_count != 1 else ''} = ${skin_val * skins_won_count:.2f}.")
                bd_lines.append(f"{winner_name} earns: ${skin_val:.2f} × {n - 1} other players × {skins_won_count} skin{'s' if skins_won_count != 1 else ''} = ${gain:.2f}")
            else:
                bd_lines = [
                    f"Valor del skin: ${skin_val:.2f} por skin. Modo: score {kind_label}.",
                    f"Hoyo {hole}: {winner_name} hizo el {kind_label} más bajo (outright, sin empate).",
                ]
                if carry_from:
                    plural_h = "s" if len(carry_from) != 1 else ""
                    bd_lines.append(f"Carry desde hoyo{plural_h} {', '.join(str(h) for h in carry_from)} (empate → se acumuló).")
                    bd_lines.append(f"Total de skins ganados en hoyo {hole}: {skins_won_count} (1 de este hoyo + {len(carry_from)} acumulados).")
                else:
                    bd_lines.append(f"Sin carry — ganó 1 skin.")
                bd_lines.append("")
                plural_s = "s" if skins_won_count != 1 else ""
                bd_lines.append(f"Cada uno de los otros {n - 1} jugadores paga ${skin_val:.2f} × {skins_won_count} skin{plural_s} = ${skin_val * skins_won_count:.2f}.")
                bd_lines.append(f"{winner_name} cobra: ${skin_val:.2f} × {n - 1} otros × {skins_won_count} skin{plural_s} = ${gain:.2f}")
            add_line("skins", detail, line_amounts, breakdown="\n".join(bd_lines))

        # Resumen de forfeits si los hay (línea informativa, sin movimiento)
        if forfeit_holes:
            holes_str = ", ".join(f"H{h}" for h in forfeit_holes)
            zero_line: dict[str, Decimal] = {p["user_id"]: ZERO for p in players}
            add_line("skins",
                _txt(lang,
                    f"📋 {forfeit_skins} skins forfeit (sin ganador al final del 18): empates en {holes_str}",
                    f"📋 {forfeit_skins} skins forfeited (no winner by hole 18): ties at {holes_str}"),
                zero_line)

    # ─── Sumar totales ────────────────────────────────────────────────────────
    for uid in bal:
        for key in ("entry_fee", "nassau", "per_hole", "prizes", "penalties", "skins", "oyes"):
            bal[uid][key] = _cents(bal[uid][key])
        bal[uid]["total"] = _cents(
            bal[uid]["entry_fee"]
            + bal[uid]["nassau"]
            + bal[uid]["per_hole"]
            + bal[uid]["prizes"]
            + bal[uid]["penalties"]
            + bal[uid]["skins"]
            + bal[uid]["oyes"]
        )

    player_total = sum((bal[uid]["total"] for uid in bal), ZERO)
    if abs(player_total + total_forfeited) > CENT:
        logging.warning(
            "balances_sum_zero_violation round_id=%s total=%s forfeited=%s",
            round_id,
            player_total,
            total_forfeited,
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
            "total_entry_fee": _cents(_money(bc.entry_fee) * n),
            "skins_value": _cents(_money(bc.skins_value)) if bc.skins_enabled else ZERO,
        },
    }


async def persist_balances(round_id: str, db: AsyncSession) -> int:
    """Calcula y persiste balances en round_player_balance.

    Usa lang='es' por default — solo persiste los NÚMEROS, no los textos
    descriptivos (esos se regeneran cuando el cliente consulta /balances con
    su locale específico).
    """
    result = await compute_balances(round_id, db, lang="es")
    if not result.get("has_bets"):
        return 0

    # Borrar persistencia previa (idempotente)
    await db.execute(delete(RoundPlayerBalance).where(RoundPlayerBalance.round_id == round_id))
    await db.flush()

    import uuid as _uuid
    count = 0
    for p in result["players"]:
        b = p["breakdown"]
        rpb = RoundPlayerBalance(
            round_id=_uuid.UUID(round_id),
            user_id=_uuid.UUID(p["user_id"]),
            entry_fee=b["entry_fee"],
            nassau_balance=b["nassau"],
            other_balance=b["per_hole"],
            birds_earned=b["prizes"],
            three_putt_loss=b["penalties"],
            skins_balance=b["skins"],
            oyes_balance=b["oyes"],
            total_balance=b["total"],
        )
        db.add(rpb)
        count += 1

    await db.flush()
    return count


async def delete_persisted_balances(round_id: str, db: AsyncSession) -> int:
    """Borra balances persistidos. Usar cuando una ronda se reabre."""
    res = await db.execute(delete(RoundPlayerBalance).where(RoundPlayerBalance.round_id == round_id))
    return res.rowcount or 0

"""
Formato "Medal Play por Equipos con puntos por posición de grupo".

Cada jugador pertenece a un EQUIPO (balanceado por handicap) y juega en un GRUPO
DE SALIDA (tee_group). Dentro de cada grupo, los jugadores compiten entre sí por su
posición NET y ganan puntos para su equipo:

    1.er lugar del grupo:  +2
    2.º lugar del grupo:   +1
    Último lugar:          -1   (SIEMPRE, sin importar el tamaño del grupo)
    Los demás:              0

Los empates dentro del grupo se rompen por TARJETA (countback) en NET "según las
ventajas": se compara el net de los últimos 9, 6, 3 hoyos, luego hoyo 18, 17… 1.
El net por hoyo ya incluye los golpes de ventaja (strokes recibidos por stroke index).

El campeón por equipos es el que acumula más puntos sumando a todos sus integrantes.

Funciones puras y sin dependencia de BD para poder probarlas en aislamiento.
"""
from typing import Optional


def countback_key(per_hole_net: dict, holes_to_play: int) -> tuple:
    """Llave de desempate por tarjeta (countback) en net. Menor = mejor.

    Devuelve (back9, back6, back3, net_h{H}, net_h{H-1}, …, net_h1).
    Los hoyos sin score cuentan 0 en el segmento (caso provisional / ronda incompleta);
    cuando ambos jugadores empatan en total normalmente jugaron los mismos hoyos.
    """
    def seg(last_n: int) -> int:
        start = max(1, holes_to_play - last_n + 1)
        return sum(per_hole_net.get(h, 0) for h in range(start, holes_to_play + 1))

    by_hole = tuple(per_hole_net.get(h, 0) for h in range(holes_to_play, 0, -1))
    return (seg(9), seg(6), seg(3)) + by_hole


def points_for_position(position: int, group_size: int) -> float:
    """Puntos para una posición (1 = mejor) dentro de un grupo de `group_size`.

    Reglas: 1°=+2, 2°=+1 (solo si no es además el último), último=-1, resto=0.
    El último SIEMPRE saca -1. En grupos de 2: 1°=+2, 2°(último)=-1.
    Grupo de 1 jugador (degenerado, sin competencia): 0.
    """
    if group_size <= 1:
        return 0.0
    if position == group_size:        # último lugar
        return -1.0
    if position == 1:
        return 2.0
    if position == 2:
        return 1.0
    return 0.0


def rank_group(players: list) -> list:
    """Ordena un grupo por net (asc) con desempate por countback y asigna posición+puntos.

    `players`: lista de dicts con al menos:
        - "total_net": int|None  (None = sin scores → va al fondo)
        - "per_hole_net": dict[int,int]
        - "holes_to_play": int
    Devuelve la misma lista (copias) ordenada, cada dict con "position", "points" y
    "tiebreak_used" (True si comparte total_net con otro y se rompió por tarjeta).
    """
    def sort_key(p):
        tn = p.get("total_net")
        # Sin scores → al fondo (total enorme), countback neutro
        if not p.get("per_hole_net"):
            return (10**9, ())
        return (tn if tn is not None else 10**9,
                countback_key(p["per_hole_net"], p.get("holes_to_play", 18)))

    ordered = sorted(players, key=sort_key)
    n = len(ordered)

    # Detectar empates de total_net (para marcar que se usó tarjeta)
    totals = [p.get("total_net") for p in ordered]

    out = []
    for idx, p in enumerate(ordered):
        position = idx + 1
        q = dict(p)
        q["position"] = position
        q["points"] = points_for_position(position, n)
        tn = p.get("total_net")
        q["tiebreak_used"] = tn is not None and totals.count(tn) > 1
        out.append(q)
    return out


def compute_team_points(players: list, holes_to_play: int) -> dict:
    """Calcula puntos por grupo y total por equipo.

    `players`: lista de dicts con:
        - user_id, name, team_number (int|None), tee_group (int|None),
          course_handicap, per_hole_net (dict[int,int]), total_net (int|None),
          holes_played (int)

    Devuelve {groups, teams, champion_team, is_tie, has_groups}.
    Solo se rankean jugadores con tee_group asignado. Jugadores sin grupo se
    listan aparte (ungrouped) y no reciben puntos.
    """
    grouped: dict = {}
    ungrouped: list = []
    for p in players:
        if p.get("tee_group") is None:
            ungrouped.append(p)
            continue
        grouped.setdefault(p["tee_group"], []).append(p)

    groups_out = []
    # Acumulador de puntos por equipo
    team_points: dict = {}
    team_meta: dict = {}

    for g in sorted(grouped.keys()):
        members = []
        for p in grouped[g]:
            members.append({
                **p,
                "holes_to_play": holes_to_play,
            })
        ranked = rank_group(members)
        complete = all(p.get("holes_played", 0) >= holes_to_play for p in grouped[g])
        group_players = []
        for r in ranked:
            tn = r.get("team_number")
            pts = r["points"]
            if tn is not None:
                team_points[tn] = team_points.get(tn, 0.0) + pts
            group_players.append({
                "user_id": r["user_id"],
                "name": r["name"],
                "team_number": tn,
                "course_handicap": r.get("course_handicap"),
                "total_net": r.get("total_net"),
                "holes_played": r.get("holes_played", 0),
                "position": r["position"],
                "points": pts,
                "tiebreak_used": r["tiebreak_used"],
            })
        groups_out.append({
            "group_number": g,
            "starting_hole": grouped[g][0].get("starting_hole"),
            "complete": complete,
            "players": group_players,
        })

    # Asegurar que todo equipo que tenga jugadores aparezca aunque sume 0
    for p in players:
        tn = p.get("team_number")
        if tn is not None and tn not in team_meta:
            team_meta[tn] = {"team_number": tn, "name": f"Equipo {tn}", "player_count": 0}
        if tn is not None:
            team_meta[tn]["player_count"] += 1

    teams_out = []
    for tn, meta in team_meta.items():
        teams_out.append({
            **meta,
            "total_points": team_points.get(tn, 0.0),
        })
    teams_out.sort(key=lambda t: -t["total_points"])

    champion_team = None
    is_tie = False
    if teams_out:
        top = teams_out[0]["total_points"]
        leaders = [t for t in teams_out if t["total_points"] == top]
        if len(leaders) == 1:
            champion_team = leaders[0]["team_number"]
        else:
            is_tie = True

    return {
        "has_groups": len(grouped) > 0,
        "groups": groups_out,
        "teams": teams_out,
        "champion_team": champion_team,
        "is_tie": is_tie,
        "ungrouped_count": len(ungrouped),
        "holes_to_play": holes_to_play,
    }

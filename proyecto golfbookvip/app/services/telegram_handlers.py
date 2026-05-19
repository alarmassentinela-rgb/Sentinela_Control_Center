"""Handlers de comandos del bot Telegram. v1.22.0.

Cada función `cmd_*` recibe (db, user) ya autenticado por chat_id y devuelve
HTML para responder. Solo lectura — sin transacciones.
"""
from datetime import date

from sqlalchemy import select, desc

from app.models.club import Club, ClubMember, MemberAccount
from app.models.handicap import HandicapHistory
from app.models.tee_time import TeeTimeBooking, TeeTimeSlot
from app.models.user import User


def _user_name(user: User) -> str:
    return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email or "Socio"


def _fmt_amount(amount: float) -> str:
    """${amount:.2f} con signo claro."""
    if amount >= 0:
        return f"+${amount:.2f}"
    return f"-${abs(amount):.2f}"


async def cmd_help(db, user: User) -> str:
    """Listado de comandos."""
    return (
        f"👋 Hola <b>{_user_name(user)}</b>\n\n"
        "Estos son los comandos disponibles:\n\n"
        "💰 /saldo — Balance en cada club\n"
        "📅 /proxima — Tu próxima reserva\n"
        "📋 /reservas — Tus próximas 5 reservas\n"
        "⛳ /handicap — Tu hándicap actual\n"
        "👤 /cuenta — Resumen de tu cuenta\n"
        "❓ /help — Esta ayuda\n\n"
        "<i>Más comandos próximamente.</i>"
    )


async def cmd_saldo(db, user: User) -> str:
    """Balance del usuario en cada club donde tiene cuenta."""
    res = await db.execute(
        select(MemberAccount, Club)
        .join(Club, Club.id == MemberAccount.club_id)
        .where(MemberAccount.user_id == user.id, MemberAccount.is_active == True)
        .order_by(Club.name)
    )
    rows = res.all()
    if not rows:
        return (
            "💼 <b>Tu saldo</b>\n\n"
            "<i>Aún no tienes cuenta en ningún club.</i>\n\n"
            "Únete a tu club desde el link de invitación que te compartieron."
        )

    lines = ["💼 <b>Tu saldo</b>", ""]
    for acc, club in rows:
        balance = float(acc.balance or 0)
        emoji = "✅" if balance >= 0 else "⚠️"
        lines.append(f"{emoji} <b>{club.name}</b>")
        lines.append(f"    Saldo: <b>{_fmt_amount(balance)}</b>")
        if acc.credit_limit and float(acc.credit_limit) > 0:
            lines.append(f"    Crédito disponible: ${float(acc.credit_limit):.2f}")
        lines.append("")
    lines.append("<i>Saldo positivo = a tu favor · Negativo = adeudo</i>")
    return "\n".join(lines)


async def cmd_proxima(db, user: User) -> str:
    """Próxima reserva confirmada del usuario en cualquier club."""
    res = await db.execute(
        select(TeeTimeBooking, TeeTimeSlot, Club)
        .join(TeeTimeSlot, TeeTimeSlot.id == TeeTimeBooking.slot_id)
        .join(Club, Club.id == TeeTimeSlot.club_id)
        .where(
            TeeTimeBooking.user_id == user.id,
            TeeTimeBooking.status == "confirmed",
            TeeTimeSlot.date >= date.today(),
        )
        .order_by(TeeTimeSlot.date, TeeTimeSlot.time)
        .limit(1)
    )
    row = res.first()
    if not row:
        return (
            "📅 <b>Tu próxima reserva</b>\n\n"
            "<i>No tienes reservas próximas.</i>\n\n"
            "Reserva un tee time desde el panel de tu club."
        )
    booking, slot, club = row
    panel_url = f"https://golfbookvip.com/es/club/{club.id}/tee-times"
    return (
        f"⛳ <b>Tu próxima reserva</b>\n\n"
        f"🏷️ <b>{club.name}</b>\n"
        f"📅 {slot.date.isoformat()} a las {slot.time.strftime('%H:%M')}\n"
        f"👥 {booking.players_count} jugador(es)\n"
        + (f"📝 <i>{booking.notes}</i>\n" if booking.notes else "")
        + f"\n<a href=\"{panel_url}\">Ver detalle</a>"
    )


async def cmd_reservas(db, user: User) -> str:
    """Lista las próximas 5 reservas del usuario."""
    res = await db.execute(
        select(TeeTimeBooking, TeeTimeSlot, Club)
        .join(TeeTimeSlot, TeeTimeSlot.id == TeeTimeBooking.slot_id)
        .join(Club, Club.id == TeeTimeSlot.club_id)
        .where(
            TeeTimeBooking.user_id == user.id,
            TeeTimeBooking.status == "confirmed",
            TeeTimeSlot.date >= date.today(),
        )
        .order_by(TeeTimeSlot.date, TeeTimeSlot.time)
        .limit(5)
    )
    rows = res.all()
    if not rows:
        return (
            "📋 <b>Tus próximas reservas</b>\n\n"
            "<i>No tienes reservas próximas.</i>"
        )
    lines = ["📋 <b>Tus próximas reservas</b>", ""]
    for b, slot, club in rows:
        lines.append(
            f"• <b>{slot.date.isoformat()}</b> {slot.time.strftime('%H:%M')} "
            f"· {club.name} ({b.players_count} jug.)"
        )
    return "\n".join(lines)


async def cmd_handicap(db, user: User) -> str:
    """Hándicap actual + tendencia (último cambio)."""
    if user.handicap_index is None:
        return (
            "⛳ <b>Tu hándicap</b>\n\n"
            "<i>Aún no tienes hándicap registrado.</i>\n\n"
            "Captura tu hándicap inicial desde tu perfil en golfbookvip.com."
        )
    hcp = float(user.handicap_index)
    # Tendencia: último registro de HandicapHistory
    h_res = await db.execute(
        select(HandicapHistory)
        .where(HandicapHistory.user_id == user.id)
        .order_by(desc(HandicapHistory.calculation_date))
        .limit(1)
    )
    last = h_res.scalar_one_or_none()
    trend_line = ""
    if last and last.previous_index is not None:
        prev = float(last.previous_index)
        delta = hcp - prev
        if abs(delta) < 0.05:
            trend_line = f"\n<i>Sin cambio desde la última ronda.</i>"
        elif delta < 0:
            trend_line = f"\n📉 <b>Bajaste {abs(delta):.1f}</b> desde la última actualización"
        else:
            trend_line = f"\n📈 Subió {delta:.1f} desde la última actualización"

    rounds_line = ""
    if user.handicap_rounds_count:
        rounds_line = f"\n<i>Calculado con {user.handicap_rounds_count} ronda(s).</i>"

    return (
        f"⛳ <b>Tu hándicap</b>\n\n"
        f"Index actual: <b>{hcp:.1f}</b>"
        + trend_line
        + rounds_line
    )


async def cmd_cuenta(db, user: User) -> str:
    """Resumen general: nombre, email, clubes activos."""
    res = await db.execute(
        select(ClubMember, Club)
        .join(Club, Club.id == ClubMember.club_id)
        .where(
            ClubMember.user_id == user.id,
            ClubMember.status == "active",
            Club.is_active == True,
        )
        .order_by(Club.name)
    )
    clubs = res.all()
    lines = [
        f"👤 <b>{_user_name(user)}</b>",
        "",
        f"📧 {user.email}",
    ]
    if user.username:
        lines.append(f"🏷️ @{user.username}")
    if user.handicap_index is not None:
        lines.append(f"⛳ HCP: {float(user.handicap_index):.1f}")
    lines.append("")
    if clubs:
        lines.append("<b>Clubes:</b>")
        for cm, club in clubs:
            badge = f" · #{cm.member_number}" if cm.member_number else ""
            lines.append(f"• {club.name}{badge}")
    else:
        lines.append("<i>No estás registrado en ningún club todavía.</i>")
    return "\n".join(lines)


async def cmd_unknown(db, user: User) -> str:
    return (
        "🤔 Comando no reconocido.\n\n"
        "Escribe /help para ver la lista de comandos disponibles."
    )


# Dispatcher
COMMANDS = {
    "/help": cmd_help,
    "/saldo": cmd_saldo,
    "/proxima": cmd_proxima,
    "/reservas": cmd_reservas,
    "/handicap": cmd_handicap,
    "/cuenta": cmd_cuenta,
}


def get_command_handler(text: str):
    """Resuelve el comando del texto (toma la primera palabra). Retorna handler o None."""
    if not text or not text.startswith("/"):
        return None
    cmd = text.split()[0].lower()
    # Soportar comandos con @botname: /saldo@GolfBookVip_bot → /saldo
    if "@" in cmd:
        cmd = cmd.split("@")[0]
    return COMMANDS.get(cmd)

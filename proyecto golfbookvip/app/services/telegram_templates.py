"""Templates HTML compactos para Telegram. v1.21.0.

Telegram acepta un subset de HTML: <b>, <i>, <u>, <s>, <a href=>, <code>, <pre>.
NO acepta <div>, <table>, ni estilos CSS.

Mantén los mensajes cortos (4-8 líneas). El emoji al inicio ayuda a leer rápido en mobile.
"""
from typing import Optional


def _fmt_date(d: str, t: str) -> str:
    return f"{d} a las {t}"


def tg_booking_confirmed(user_name: str, club_name: str, slot_date: str,
                          slot_time: str, players: list[dict],
                          total_charged: float, panel_url: str) -> str:
    """players: [{name, player_type, fee_amount}]"""
    lines = [
        f"⛳ <b>Reserva confirmada</b>",
        f"",
        f"<b>{club_name}</b>",
        f"📅 {_fmt_date(slot_date, slot_time)}",
        f"",
        f"<b>Jugadores:</b>",
    ]
    for p in players:
        type_lbl = "socio" if p['player_type'] == 'member' else ("invitado" if p['player_type'] == 'guest' else "público")
        fee_str = f" · ${p['fee_amount']:.0f}" if p['fee_amount'] > 0 else ""
        lines.append(f"• {p['name']} <i>({type_lbl}{fee_str})</i>")
    if total_charged > 0:
        lines.append("")
        lines.append(f"💰 <b>Total cobrado:</b> ${total_charged:.0f}")
    lines.append("")
    lines.append(f'<a href="{panel_url}">Ver detalle</a>')
    return "\n".join(lines)


def tg_booking_cancelled(user_name: str, club_name: str, slot_date: str,
                          slot_time: str, refunded_total: float, panel_url: str) -> str:
    lines = [
        f"❌ <b>Reserva cancelada</b>",
        f"",
        f"<b>{club_name}</b>",
        f"📅 {_fmt_date(slot_date, slot_time)}",
    ]
    if refunded_total > 0:
        lines.append("")
        lines.append(f"💸 Reembolsado: ${refunded_total:.0f} a tu cuenta")
    lines.append("")
    lines.append(f'<a href="{panel_url}">Ver tee times</a>')
    return "\n".join(lines)


def tg_welcome_to_club(user_name: str, club_name: str, panel_url: str,
                        invite_link: Optional[str] = None) -> str:
    lines = [
        f"🎉 <b>¡Bienvenido a {club_name}!</b>",
        f"",
        f"Hola {user_name}, ya eres socio activo del club en GolfBookVIP.",
        f"",
        f"Desde tu panel puedes:",
        f"• Reservar tee times",
        f"• Ver tu estado de cuenta",
        f"• Jugar rondas con otros socios",
        f"",
        f'<a href="{panel_url}">Ir al panel del club</a>',
    ]
    return "\n".join(lines)


def tg_tee_time_reminder(user_name: str, club_name: str, slot_date: str,
                          slot_time: str, hours_until: int, panel_url: str) -> str:
    when = "en 24 horas" if hours_until >= 12 else "en 1 hora"
    emoji = "⏰" if hours_until >= 12 else "🚨"
    lines = [
        f"{emoji} <b>Recordatorio · Tee time {when}</b>",
        f"",
        f"<b>{club_name}</b>",
        f"📅 {_fmt_date(slot_date, slot_time)}",
        f"",
        f'<a href="{panel_url}">Ver detalles</a>',
        f"",
        f"<i>¡Buen golf!</i>",
    ]
    return "\n".join(lines)


def tg_account_linked() -> str:
    return (
        "✅ <b>¡Vinculación exitosa!</b>\n\n"
        "Tu cuenta de GolfBookVIP está conectada a este chat.\n"
        "Te enviaré aquí tus notificaciones importantes: reservas, recordatorios, cargos y avisos del club.\n\n"
        "Puedes desactivar Telegram cuando quieras desde tu perfil en golfbookvip.com."
    )


def tg_account_unlinked() -> str:
    return (
        "👋 Tu cuenta de GolfBookVIP fue desvinculada de este chat.\n"
        "Si fue un error, ve a tu perfil en golfbookvip.com y vuelve a conectar Telegram."
    )


def tg_link_invalid() -> str:
    return (
        "❌ Token de vinculación inválido o expirado.\n\n"
        "Genera uno nuevo desde tu perfil en <a href=\"https://golfbookvip.com/es/profile\">golfbookvip.com</a>."
    )

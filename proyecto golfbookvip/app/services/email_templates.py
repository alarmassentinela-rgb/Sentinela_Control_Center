"""Templates de email para notificaciones de GolfBookVIP. HTML inline simple,
table-based para máxima compatibilidad con clientes de email."""
from typing import Optional


_BASE_STYLE = """
<style>
body { margin: 0; padding: 0; background: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
.wrap { width: 100%; background: #f5f5f5; padding: 24px 0; }
.card { max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; }
.brand { background: #10b981; color: white; padding: 18px 24px; }
.brand h1 { margin: 0; font-size: 18px; font-weight: 700; }
.body { padding: 24px; color: #18181b; line-height: 1.5; font-size: 14px; }
.body h2 { margin: 0 0 8px 0; font-size: 20px; color: #18181b; }
.body p { margin: 0 0 12px 0; }
.box { background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; padding: 14px; margin: 14px 0; }
.box-warn { background: #fef3c7; border-color: #fcd34d; }
.box-red { background: #fee2e2; border-color: #fca5a5; }
.row { padding: 6px 0; font-size: 13px; }
.row .lbl { color: #71717a; display: inline-block; min-width: 90px; }
.btn { display: inline-block; background: #10b981; color: white !important; padding: 10px 18px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; }
.footer { padding: 18px 24px; background: #fafafa; border-top: 1px solid #e4e4e7; font-size: 11px; color: #71717a; text-align: center; }
.muted { color: #71717a; font-size: 12px; }
</style>
"""

_FOOTER = """
<div class="footer">
  Recibes este email porque eres usuario de <strong>GolfBookVIP</strong>.<br>
  Para dejar de recibir estos avisos, contacta a tu club o escribe a contacto@golfbookvip.com.
</div>
"""


def _shell(title: str, body_html: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  {_BASE_STYLE}
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="brand"><h1>⛳ GolfBookVIP</h1></div>
      <div class="body">{body_html}</div>
      {_FOOTER}
    </div>
  </div>
</body>
</html>"""


def _fmt_date(d: str, t: str) -> str:
    """Espera ISO date '2026-05-20' y time '07:30'."""
    return f"{d} a las {t}"


def tpl_booking_confirmed(user_name: str, club_name: str, slot_date: str,
                            slot_time: str, players_list: list[dict],
                            total_charged: float, panel_url: str) -> tuple[str, str]:
    """Retorna (subject, html). players_list: [{name, player_type, fee_amount}]"""
    subject = f"Reserva confirmada · {club_name} · {slot_date} {slot_time}"
    players_rows = ""
    for p in players_list:
        type_lbl = "Socio" if p['player_type'] == 'member' else ("Invitado" if p['player_type'] == 'guest' else "Público")
        fee_str = f"${p['fee_amount']:.0f}" if p['fee_amount'] > 0 else "—"
        players_rows += f"<div class='row'><span class='lbl'>· {p['name']}</span>{type_lbl} · {fee_str}</div>"

    total_html = ""
    if total_charged > 0:
        total_html = f"""<div class="box box-warn">
          <strong>Total cobrado:</strong> ${total_charged:.0f}<br>
          <span class="muted">Cargado a la cuenta del responsable. Puedes verlo en tu estado de cuenta del club.</span>
        </div>"""

    body = f"""
      <h2>Hola {user_name},</h2>
      <p>Tu reserva en <strong>{club_name}</strong> está confirmada.</p>
      <div class="box">
        <div class="row"><span class="lbl">Fecha:</span><strong>{_fmt_date(slot_date, slot_time)}</strong></div>
        <div class="row"><span class="lbl">Jugadores:</span></div>
        {players_rows}
      </div>
      {total_html}
      <p><a class="btn" href="{panel_url}">Ver mi reserva</a></p>
      <p class="muted">¡Buen golf!</p>
    """
    return subject, _shell(subject, body)


def tpl_booking_cancelled(user_name: str, club_name: str, slot_date: str,
                            slot_time: str, refunded_total: float, panel_url: str) -> tuple[str, str]:
    subject = f"Reserva cancelada · {club_name} · {slot_date} {slot_time}"
    refund_html = ""
    if refunded_total > 0:
        refund_html = f"""<div class="box">
          <strong>Reembolsado:</strong> ${refunded_total:.0f} a tu cuenta del club.
        </div>"""
    body = f"""
      <h2>Hola {user_name},</h2>
      <p>Tu reserva en <strong>{club_name}</strong> del {_fmt_date(slot_date, slot_time)} fue cancelada.</p>
      {refund_html}
      <p><a class="btn" href="{panel_url}">Ver tee times disponibles</a></p>
    """
    return subject, _shell(subject, body)


def tpl_welcome_to_club(user_name: str, club_name: str, panel_url: str,
                         invite_link: Optional[str] = None) -> tuple[str, str]:
    subject = f"Bienvenido a {club_name} en GolfBookVIP"
    invite_html = ""
    if invite_link:
        invite_html = f"""<p class="muted">Comparte este link con otros socios de tu club para que se unan:<br>
        <code>{invite_link}</code></p>"""
    body = f"""
      <h2>¡Bienvenido, {user_name}!</h2>
      <p>Acabas de ser registrado como socio del <strong>{club_name}</strong> en GolfBookVIP.</p>
      <div class="box">
        <p style="margin:0">Desde tu panel del club puedes:</p>
        <ul style="margin:6px 0; padding-left:18px">
          <li>Reservar tee times</li>
          <li>Ver tu estado de cuenta</li>
          <li>Conocer las apuestas y rondas con otros socios</li>
        </ul>
      </div>
      <p><a class="btn" href="{panel_url}">Ir al panel del club</a></p>
      {invite_html}
    """
    return subject, _shell(subject, body)


def tpl_tee_time_reminder(user_name: str, club_name: str, slot_date: str,
                            slot_time: str, hours_until: int, panel_url: str) -> tuple[str, str]:
    when = "en 24 horas" if hours_until >= 12 else "en 1 hora"
    subject = f"Recordatorio · Tee time {when} · {club_name}"
    body = f"""
      <h2>Hola {user_name},</h2>
      <p>Te recordamos que tienes una reserva en <strong>{club_name}</strong> <strong>{when}</strong>.</p>
      <div class="box">
        <div class="row"><span class="lbl">Fecha:</span><strong>{_fmt_date(slot_date, slot_time)}</strong></div>
      </div>
      <p><a class="btn" href="{panel_url}">Ver detalles</a></p>
      <p class="muted">¡Buen golf!</p>
    """
    return subject, _shell(subject, body)

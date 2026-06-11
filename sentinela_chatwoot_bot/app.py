"""Bot de reportes Sentinela — AgentBot de Chatwoot.

Flujo: WhatsApp (8688225875) → EvoApi → inbox "Reportes Sentinela" en Chatwoot →
Chatwoot reenvía cada mensaje entrante a este webhook. El bot:
  1. Identifica al cliente por teléfono (Odoo XML-RPC).
  2. Crea la orden FSM (repair/Nuevo) y confirma el folio. Sin match → orden POR CONCILIAR.
  3. Deja una nota interna con la ficha del cliente para recepción.
  4. Handoff: en horario de oficina asigna a soporte y abre la conversación; el
     cliente puede pedir "asesor" en cualquier momento para hablar con un humano.

Seguridad: el contenedor NO publica puerto; solo el rails de Chatwoot (misma red
docker) puede alcanzar el webhook.
"""

import logging
from datetime import datetime

from fastapi import FastAPI, Request

import config
import chatwoot
import odoo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("chatwoot_bot.app")

app = FastAPI(title="Sentinela Chatwoot FSM Bot")

# Dedup en memoria para reintentos rápidos del webhook (la verdad persistente entre
# reinicios es el status 'open' de la conversación tras el handoff).
_handled: set[int] = set()

# ── Mensajes ───────────────────────────────────────────────────────
MSG_ASK_DETAIL = (
    "¡Hola! 👋 Soy el asistente de *Sentinela*. "
    "Cuéntame por favor qué problema tienes con tu servicio (con el mayor detalle "
    "posible) y levanto tu reporte. Si prefieres hablar con un asesor, escribe *ASESOR*."
)
MSG_HANDOFF = (
    "Con gusto. 🧑‍💼 Te comunico con un asesor; en breve te atiende una persona del equipo."
)
MSG_FOLIO_OFFICE = (
    "✅ Listo{name}, levantamos tu reporte con folio *{folio}*.\n"
    "Un asesor te dará seguimiento en breve (horario de oficina). "
    "Si necesitas algo más, aquí estoy."
)
MSG_FOLIO_AFTERHOURS = (
    "✅ Listo{name}, registramos tu reporte con folio *{folio}*.\n"
    "En este momento estamos fuera de horario de oficina; un asesor te contacta al "
    "iniciar el siguiente día hábil. Gracias por tu paciencia. 🙏"
)
MSG_ERROR = (
    "Recibimos tu mensaje pero tuvimos un problema al registrar el reporte en el "
    "sistema. No te preocupes: ya avisamos a un asesor para que lo levante a mano."
)

_GREETINGS = {"hola", "buenas", "buenos dias", "buenos días", "buenas tardes",
              "buenas noches", "hey", "hi", "ola", "que tal", "qué tal", "saludos"}


def _office_hours_now() -> bool:
    now = datetime.now(config.TZ)
    return now.weekday() in config.OFFICE_DAYS and config.OFFICE_START <= now.hour < config.OFFICE_END


def _is_greeting(content: str) -> bool:
    c = content.strip().lower().rstrip("!.¡¿? ")
    return len(c) < 14 and (c in _GREETINGS or any(c.startswith(g) for g in _GREETINGS))


def _wants_human(content: str) -> bool:
    c = content.lower()
    return any(k in c for k in config.HANDOFF_KEYWORDS)


def _extract(payload: dict) -> dict:
    """Normaliza los campos que nos importan del evento de Chatwoot."""
    conv = payload.get("conversation") or {}
    sender = payload.get("sender") or {}
    meta_sender = (conv.get("meta") or {}).get("sender") or {}
    phone = sender.get("phone_number") or meta_sender.get("phone_number") or \
        sender.get("identifier") or meta_sender.get("identifier") or ""
    return {
        "event": payload.get("event"),
        "message_type": payload.get("message_type"),
        "content": (payload.get("content") or "").strip(),
        "conv_id": conv.get("id"),
        "inbox_id": conv.get("inbox_id") or (payload.get("inbox") or {}).get("id"),
        "status": conv.get("status"),
        "phone": phone,
        "name": sender.get("name") or meta_sender.get("name") or "",
    }


def _post_client_note(conv_id: int, phone: str):
    """Nota interna con la ficha Odoo del cliente para que recepción tenga contexto."""
    try:
        summary = odoo.get_client_summary(phone)
    except Exception as e:
        logger.error("ficha Odoo error: %s", e)
        summary = None
    if summary:
        chatwoot.send_message(conv_id, f"🗂️ *Ficha del cliente (Odoo)*\n{summary}", private=True)


def _process(payload: dict):
    d = _extract(payload)

    # Solo mensajes ENTRANTES de cliente.
    if d["event"] != "message_created" or d["message_type"] != "incoming":
        return
    conv_id = d["conv_id"]
    if not conv_id:
        return
    # Filtrar al inbox que atendemos.
    if config.CHATWOOT_INBOX_ID and d["inbox_id"] and d["inbox_id"] != config.CHATWOOT_INBOX_ID:
        return

    content = d["content"]

    # Guarda de idempotencia: si la conversación ya está open/resolved, el reporte ya
    # se levantó (handoff) o un humano la tomó → el bot calla. El status viene en el
    # payload y es lo único de idempotencia que el AgentBot puede leer Y escribir
    # (no puede GET la conversación ni poner etiquetas). `_handled` cubre reintentos
    # del mismo proceso antes de que el status open propague.
    if conv_id in _handled or d["status"] in ("open", "resolved"):
        logger.info("conv %s status=%s ya atendida; bot en silencio", conv_id, d["status"])
        return

    # Cliente pide hablar con una persona → handoff inmediato, sin crear orden.
    if _wants_human(content):
        chatwoot.send_message(conv_id, MSG_HANDOFF)
        chatwoot.assign_team(conv_id, config.HANDOFF_TEAM_ID)
        chatwoot.toggle_status(conv_id, "open")
        _handled.add(conv_id)
        return

    # Saludo escueto sin detalle → pedir que describa, sin generar orden basura.
    if _is_greeting(content):
        chatwoot.send_message(conv_id, MSG_ASK_DETAIL)
        return

    # ── Intake: crear la orden FSM ──
    partner = odoo.find_partner_by_phone(d["phone"]) if d["phone"] else None
    if partner:
        sub_id = odoo.get_single_active_subscription_id(partner["id"])
        desc = f"Reporte por WhatsApp (tel: {d['phone']}).\n---\n{content}"
        res = odoo.create_fsm_order(partner["id"], desc, "repair", sub_id)
        first = (partner.get("name") or "").split()
        greeting = f" {first[0]}" if first else ""
    else:
        res = odoo.create_reconcile_fsm_order(d["phone"], content, d["name"])
        greeting = ""

    if not res or not res.get("ok"):
        logger.error("conv %s: fallo al crear orden FSM", conv_id)
        chatwoot.send_message(conv_id, MSG_ERROR)
        chatwoot.assign_team(conv_id, config.HANDOFF_TEAM_ID)
        chatwoot.toggle_status(conv_id, "open")
        return

    folio = res["name"]
    _handled.add(conv_id)

    # Confirmación al cliente (honesta según horario).
    tmpl = MSG_FOLIO_OFFICE if _office_hours_now() else MSG_FOLIO_AFTERHOURS
    chatwoot.send_message(conv_id, tmpl.format(name=greeting, folio=folio))

    # Ficha del cliente para recepción (nota interna).
    _post_client_note(conv_id, d["phone"])

    # Handoff a soporte: asignar el team y ABRIR la conversación SIEMPRE. El status
    # 'open' es la guarda de idempotencia (los siguientes mensajes ya no re-disparan
    # el intake) y deja la conversación en la cola del equipo. Fuera de horario nadie
    # la atiende hasta el día hábil, pero ya está encolada y el cliente fue avisado.
    chatwoot.assign_team(conv_id, config.HANDOFF_TEAM_ID)
    chatwoot.toggle_status(conv_id, "open")
    logger.info("conv %s: orden %s creada (match=%s)", conv_id, folio, bool(partner))


@app.post("/chatwoot/agentbot")
async def agentbot(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return {"status": "bad-json"}
    try:
        _process(payload)
    except Exception as e:
        logger.exception("error procesando evento: %s", e)
    return {"status": "ok"}


@app.get("/status")
async def status():
    uid = None
    try:
        uid = odoo._get_uid()
    except Exception:
        pass
    return {
        "service": "sentinela-chatwoot-bot",
        "odoo": "ok" if uid else "error",
        "inbox_id": config.CHATWOOT_INBOX_ID,
        "office_hours_now": _office_hours_now(),
        "bot_token_set": bool(config.CHATWOOT_BOT_TOKEN),
        "handled_in_memory": len(_handled),
    }

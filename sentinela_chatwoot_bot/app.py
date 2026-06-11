"""Bot de reportes Sentinela — AgentBot de Chatwoot, con IA conversacional.

Flujo: WhatsApp (8688225875) → EvoApi → inbox "Reportes Sentinela" → Chatwoot
reenvía cada mensaje entrante a este webhook. El bot mantiene la conversación con
un LLM (OpenRouter): saluda, pregunta, junta el detalle de la falla, confirma y
SOLO entonces levanta la orden FSM en Odoo. Luego hace handoff a soporte.

El LLM responde un JSON {action, message, summary}:
  - reply         → solo le responde al cliente.
  - create_ticket → crea la orden con `summary`, confirma el folio, handoff a soporte.
  - handoff       → pasa la conversación a un humano (sin crear orden).

Seguridad: el contenedor NO publica puerto; solo el rails de Chatwoot lo alcanza.
"""

import json
import logging
import re
from datetime import datetime

from fastapi import FastAPI, Request

import config
import chatwoot
import odoo
import llm
import state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("chatwoot_bot.app")

app = FastAPI(title="Sentinela Chatwoot FSM Bot")

# Dedup en memoria para reintentos rápidos (la verdad persistente entre reinicios es
# el status 'open' de la conversación tras el handoff + el folio guardado en state).
_handled: set[int] = set()

# ── Mensajes de plantilla (folio/handoff/error los controla el bot, no el LLM) ──
MSG_HANDOFF = (
    "Con gusto. 🧑‍💼 Te comunico con un asesor; en breve te atiende una persona del equipo."
)
MSG_FOLIO_OFFICE = (
    "✅ Listo{name}, levantamos tu reporte con folio *{folio}*.\n"
    "Un asesor le dará seguimiento en breve. Si necesitas algo más, aquí estoy."
)
MSG_FOLIO_AFTERHOURS = (
    "✅ Listo{name}, registramos tu reporte con folio *{folio}*.\n"
    "Estamos fuera de horario de oficina; un asesor te contacta el siguiente día hábil. "
    "Gracias por tu paciencia. 🙏"
)
MSG_ERROR = (
    "Recibí tu mensaje pero tuve un problema al registrar el reporte en el sistema. "
    "No te preocupes: ya avisé a un asesor para que lo levante a mano."
)
MSG_LLM_FALLBACK = (
    "¡Hola! 👋 Soy el asistente de *Sentinela*. Cuéntame por favor qué problema tienes "
    "con tu servicio y con gusto levanto tu reporte."
)


def _office_hours_now() -> bool:
    now = datetime.now(config.TZ)
    return now.weekday() in config.OFFICE_DAYS and config.OFFICE_START <= now.hour < config.OFFICE_END


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
        "has_attachment": bool(payload.get("attachments")),
    }


def _resolve_client(phone: str):
    """Devuelve (partner|None, ficha_texto, primer_nombre) para el system prompt."""
    partner = odoo.find_partner_by_phone(phone) if phone else None
    if not partner:
        return None, "Cliente no identificado por su número (sin cuenta ligada).", ""
    try:
        ficha = odoo.get_client_summary(phone) or ""
    except Exception as e:
        logger.error("ficha Odoo error: %s", e)
        ficha = ""
    first = (partner.get("name") or "").split()
    name = first[0] if first else ""
    return partner, (ficha or f"Cliente: {partner.get('name','')}"), name


def _parse_llm(raw: str) -> dict:
    """Extrae el JSON de la respuesta del LLM de forma tolerante."""
    if not raw:
        return {}
    txt = raw.strip()
    # quitar fences ```json ... ```
    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt, flags=re.IGNORECASE).strip()
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}


def _llm_decide(conv_id: int, name: str, ficha: str, order_folio: str | None = None) -> dict:
    """Arma el contexto (system + historial) y pide la decisión al LLM."""
    system = config.SYSTEM_PROMPT.format(name=name or "(desconocido)", ficha=ficha)
    if order_folio:
        # Ya hay reporte: el bot atiende follow-ups, NO crea otra orden.
        system += (
            f"\n\nIMPORTANTE: Ya se levantó el reporte de este cliente con folio {order_folio}. "
            "NO uses create_ticket otra vez. Responde sus dudas o follow-ups de forma breve y "
            "útil (p.ej. que un técnico revisará el reporte y lo contactará para coordinar la "
            "visita; NO des tiempos exactos de llegada). Si pide hablar con una persona, o "
            "necesita algo que tú no puedes resolver, usa handoff."
        )
    messages = [{"role": "system", "content": system}]
    messages += state.get_history(conv_id, config.HISTORY_LIMIT)
    raw = llm.chat_completion(messages, json_mode=True)
    data = _parse_llm(raw)
    if data and data.get("action"):
        return data
    # No parseó como JSON: si el modelo dijo algo, relévalo como respuesta (evita el
    # bucle del mensaje robótico); si vino vacío, usa el fallback.
    if raw:
        return {"action": "reply", "message": raw}
    return {"action": "reply", "message": MSG_LLM_FALLBACK}


def _create_order(d: dict, partner, decision: dict) -> dict | None:
    """Crea la orden con todo lo que juntó el bot: problema + servicio/domicilio
    reportado, horario de contacto y teléfono alterno; liga la sub y su domicilio."""
    summary = decision.get("summary") or d["content"]
    sub_name = (decision.get("subscription") or "").strip()
    contact_time = (decision.get("contact_time") or "").strip()
    alt_phone = (decision.get("alt_phone") or "").strip()

    extras = []
    if sub_name:
        extras.append(f"Servicio/domicilio reportado: {sub_name}")
    if contact_time:
        extras.append(f"Horario de contacto preferido: {contact_time}")
    if alt_phone:
        extras.append(f"Teléfono alterno: {alt_phone}")
    body = ("\n".join(extras) + "\n---\n" + summary) if extras else summary

    if not partner:
        return odoo.create_reconcile_fsm_order(d["phone"], body, d["name"])

    sub_id = None
    addr_id = None
    if sub_name:
        found = odoo.find_subscription(partner["id"], sub_name)
        if found:
            sub_id = found["id"]
            sa = found.get("service_address_id")
            addr_id = sa[0] if sa else None
    if not sub_id:
        sub_id = odoo.get_single_active_subscription_id(partner["id"])
    desc = f"Reporte por WhatsApp (tel: {d['phone']}).\n---\n{body}"
    return odoo.create_fsm_order(partner["id"], desc, "repair", sub_id, addr_id)


def _do_handoff(conv_id: int, message: str | None):
    chatwoot.send_message(conv_id, message or MSG_HANDOFF)
    chatwoot.assign_team(conv_id, config.HANDOFF_TEAM_ID)
    chatwoot.toggle_status(conv_id, "open")
    _handled.add(conv_id)


def _process(payload: dict):
    d = _extract(payload)

    # Solo mensajes ENTRANTES de cliente.
    if d["event"] != "message_created" or d["message_type"] != "incoming":
        return
    conv_id = d["conv_id"]
    if not conv_id:
        return
    if config.CHATWOOT_INBOX_ID and d["inbox_id"] and d["inbox_id"] != config.CHATWOOT_INBOX_ID:
        return

    # Idempotencia: tras el handoff la conversación queda 'open'/'resolved' → bot calla.
    if conv_id in _handled or d["status"] in ("open", "resolved"):
        logger.info("conv %s status=%s ya atendida; bot en silencio", conv_id, d["status"])
        return

    content = d["content"]
    if not content:
        # Mensaje sin texto: si trae adjunto (foto del módem, nota de voz, etc.) el bot
        # NO debe quedarse mudo — deja que el LLM pida una descripción por escrito.
        # (Pendiente futuro: visión para fotos / STT para audios, como en OpenClaw.)
        if d["has_attachment"]:
            content = "(El cliente envió un archivo adjunto —foto/audio/etc.— sin texto.)"
        else:
            return

    # Guardar el turno del cliente en el historial.
    state.add_message(conv_id, "user", content)

    # Atajo duro: el cliente SIEMPRE puede escapar a un humano, pase lo que pase el LLM.
    if _wants_human(content):
        _do_handoff(conv_id, MSG_HANDOFF)
        return

    # Contexto del cliente (Odoo) + decisión del LLM. Si ya hay folio, el bot sigue
    # activo para follow-ups (no creó handoff al crear el ticket).
    existing_folio = state.get_order(conv_id)
    partner, ficha, name = _resolve_client(d["phone"])
    decision = _llm_decide(conv_id, name, ficha, existing_folio)
    action = (decision.get("action") or "reply").lower()
    message = decision.get("message") or ""

    # ── HANDOFF (sí suelta a humano: cliente lo pide o el bot no puede resolver) ──
    if action == "handoff":
        _do_handoff(conv_id, message or MSG_HANDOFF)
        logger.info("conv %s: handoff (IA)", conv_id)
        return

    # ── CREATE_TICKET ──
    if action == "create_ticket":
        if existing_folio:  # ya se creó antes; no duplicar, solo responde
            reply = message or f"Tu reporte ya quedó registrado con folio *{existing_folio}*. 🙌"
            chatwoot.send_message(conv_id, reply)
            state.add_message(conv_id, "assistant", reply)
            return
        res = _create_order(d, partner, decision)
        if not res or not res.get("ok"):
            logger.error("conv %s: fallo al crear orden FSM", conv_id)
            chatwoot.send_message(conv_id, MSG_ERROR)
            _do_handoff(conv_id, None)
            return
        folio = res["name"]
        state.set_order(conv_id, folio)
        greet = f" {name}" if name else ""
        tmpl = MSG_FOLIO_OFFICE if _office_hours_now() else MSG_FOLIO_AFTERHOURS
        folio_msg = tmpl.format(name=greet, folio=folio)
        chatwoot.send_message(conv_id, folio_msg)
        state.add_message(conv_id, "assistant", folio_msg)
        _post_client_note(conv_id, d["phone"])
        # Asigna a soporte para ruteo, pero NO suelta a humano todavía: la conversación
        # queda en 'pending' y el bot sigue atendiendo los follow-ups del cliente.
        chatwoot.assign_team(conv_id, config.HANDOFF_TEAM_ID)
        logger.info("conv %s: orden %s creada (match=%s); bot sigue activo", conv_id, folio, bool(partner))
        return

    # ── REPLY (default) ──
    reply = message or MSG_LLM_FALLBACK
    chatwoot.send_message(conv_id, reply)
    state.add_message(conv_id, "assistant", reply)


def _post_client_note(conv_id: int, phone: str):
    """Nota interna con la ficha Odoo del cliente para recepción."""
    try:
        summary = odoo.get_client_summary(phone)
    except Exception as e:
        logger.error("ficha Odoo error: %s", e)
        summary = None
    if summary:
        chatwoot.send_message(conv_id, f"🗂️ *Ficha del cliente (Odoo)*\n{summary}", private=True)


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
        "llm": "ok" if config.OPENROUTER_API_KEY else "no-key",
        "inbox_id": config.CHATWOOT_INBOX_ID,
        "office_hours_now": _office_hours_now(),
        "bot_token_set": bool(config.CHATWOOT_BOT_TOKEN),
        "handled_in_memory": len(_handled),
    }

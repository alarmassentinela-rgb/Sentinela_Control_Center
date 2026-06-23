"""Bot de primera línea Sentinela — AgentBot de Chatwoot, con IA conversacional.

Flujo: WhatsApp (8688225875) → EvoApi → inbox "Reportes Sentinela" → Chatwoot
reenvía cada mensaje entrante a este webhook. El bot mantiene la conversación con
un LLM (OpenRouter). Su PRIMERA tarea es un TRIAGE de intención (soporte / ventas /
administración) y atiende cada carril distinto, ruteando el seguimiento a la persona
correcta.

El LLM responde un JSON {action, topic, message, ...}:
  - reply         → solo le responde al cliente.
  - create_ticket → SOPORTE: crea la orden FSM con `summary`, da el folio, sigue activo.
  - create_lead   → VENTAS: crea una oportunidad CRM (a Enrique Garza Bedolla) y rutea.
  - handoff       → pasa la conversación a un humano por tema (admin → Irma, etc.).

Seguridad: el contenedor NO publica puerto; solo el rails de Chatwoot lo alcanza.
"""

import base64
import json
import logging
import re
from datetime import datetime, timedelta

import httpx
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
# Cola de atención: dentro de horario te atienden "en breve"; fuera de horario el
# texto es honesto y dice cuándo (no promete atención inmediata).
MSG_HANDOFF_OFFICE = (
    "Con gusto. 🧑‍💼 Te comunico con {area}; en breve te atiende una persona del equipo por aquí."
)
MSG_HANDOFF_AFTERHOURS = (
    "Con gusto te paso con {area}. 🧑‍💼 En este momento estamos fuera de horario de atención "
    "({hours}); tu caso queda en cola y te contactan {when}. Gracias por tu paciencia. 🙏"
)
# Nombre legible del área para el mensaje al cliente.
AREA_NAMES = {
    "soporte": "soporte técnico", "cobranza": "cobranza",
    "facturacion": "facturación", "ventas": "ventas",
}
MSG_FOLIO_OFFICE = (
    "✅ Listo{name}, levantamos tu reporte con folio *{folio}*.\n"
    "Un asesor le dará seguimiento en breve. Si necesitas algo más, aquí estoy."
)
MSG_FOLIO_AFTERHOURS = (
    "✅ Listo{name}, registramos tu reporte con folio *{folio}*.\n"
    "En este momento estamos fuera de horario ({hours}); un asesor te dará seguimiento {when}. "
    "Gracias por tu paciencia. 🙏"
)
MSG_ERROR = (
    "Recibí tu mensaje pero tuve un problema al registrar el reporte en el sistema. "
    "No te preocupes: ya avisé a un asesor para que lo levante a mano."
)
MSG_LLM_FALLBACK = (
    "¡Hola! 👋 Soy el asistente de *Sentinela*. Cuéntame por favor en qué te puedo ayudar: "
    "¿es una falla de tu servicio, quieres contratar/cotizar algo, o es un tema de tu cuenta?"
)
# Ventas: se registró la oportunidad y un asesor de ventas dará seguimiento.
MSG_LEAD_OFFICE = (
    "✅ Listo{name}, registramos tu solicitud. Un asesor de ventas te contactará en breve "
    "para confirmarte cobertura y precio. 🙌"
)
MSG_LEAD_AFTERHOURS = (
    "✅ Listo{name}, registramos tu solicitud de información. En este momento estamos fuera de "
    "horario ({hours}); un asesor de ventas te contactará {when}. 🙏"
)
MSG_ERROR_LEAD = (
    "Recibí tu interés pero tuve un problema al registrarlo en el sistema. No te preocupes: "
    "ya avisé a un asesor de ventas para que te contacte."
)


_DAY_NAMES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _office_hours_now() -> bool:
    now = datetime.now(config.TZ)
    rng = config.OFFICE_SCHEDULE.get(now.weekday())
    return bool(rng and rng[0] <= now.hour < rng[1])


def _next_office_open() -> str:
    """Texto humano del próximo momento de atención: 'hoy a las 9:00', 'mañana a
    las 9:00' o 'el lunes a las 9:00'. Para usar fuera de horario."""
    now = datetime.now(config.TZ)
    for i in range(0, 8):
        day = now + timedelta(days=i)
        rng = config.OFFICE_SCHEDULE.get(day.weekday())
        if not rng:
            continue
        start, _end = rng
        if i == 0 and now.hour >= start:
            continue  # hoy ya abrimos; toca otro día
        if i == 0:
            return f"hoy a las {start}:00"
        if i == 1:
            return f"mañana a las {start}:00"
        return f"el {_DAY_NAMES[day.weekday()]} a las {start}:00"
    return "en horario de oficina"


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
        "image_urls": [a.get("data_url") for a in (payload.get("attachments") or [])
                       if a.get("data_url") and (a.get("file_type") in ("image", 0))],
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


def _salvage_message(raw: str) -> str:
    """Rescata el valor de `message` de una respuesta JSON malformada/truncada del
    LLM, para NUNCA reenviarle JSON crudo (ni un '{') al cliente. '' si no se puede."""
    if not raw:
        return ""
    m = re.search(r'"message"\s*:\s*"((?:[^"\\]|\\.)*)"', raw, flags=re.DOTALL)
    if not m:
        return ""
    try:
        return json.loads('"' + m.group(1) + '"')
    except Exception:
        return m.group(1).strip()


def _llm_decide(conv_id: int, name: str, ficha: str, order_folio: str | None = None,
                verified: bool = True, lead_ref: str | None = None) -> dict:
    """Arma el contexto (system + historial) y pide la decisión al LLM.
    verified=False (número no encontrado en Odoo) → prompt restringido: NO da info de
    cuenta, solo recaba datos para un reporte interno (VERIFICAR IDENTIDAD)."""
    base = config.SYSTEM_PROMPT if verified else config.SYSTEM_PROMPT_UNVERIFIED
    system = base.format(name=name or "(desconocido)", ficha=ficha)
    # Conciencia de horario: el bot atiende 24/7 pero los asesores humanos NO.
    if _office_hours_now():
        system += (f"\n\nHORARIO DE ATENCIÓN HUMANA: {config.OFFICE_HOURS_TEXT}. "
                   "AHORA MISMO estamos DENTRO de horario: si pasas con un asesor o prometes "
                   "seguimiento, di que lo atienden en breve.")
    else:
        system += (f"\n\nHORARIO DE ATENCIÓN HUMANA: {config.OFFICE_HOURS_TEXT}. "
                   f"AHORA MISMO estamos FUERA de horario; el próximo horario hábil es {_next_office_open()}. "
                   "NUNCA prometas atención inmediata de un asesor: di con claridad que su reporte queda "
                   "registrado y que un asesor lo contactará en el próximo horario hábil. El soporte "
                   "automático (diagnóstico, levantar el folio) SÍ sigue disponible ahora.")
    if order_folio:
        # Ya hay reporte: el bot atiende follow-ups, NO crea otra orden.
        system += (
            f"\n\nIMPORTANTE: Ya se levantó el reporte de este cliente con folio {order_folio}. "
            "NO uses create_ticket otra vez para la MISMA falla. Responde sus dudas o follow-ups de "
            "forma breve y útil (p.ej. que un técnico revisará el reporte y lo contactará para "
            "coordinar la visita; NO des tiempos exactos de llegada). Si pide hablar con una "
            "persona, o necesita algo que tú no puedes resolver, usa handoff."
        )
    if lead_ref:
        # Ya se registró un lead de ventas: no dupliques, pero SÍ atiende otros temas.
        system += (
            "\n\nIMPORTANTE: Ya registraste una solicitud de VENTAS de este cliente. NO uses "
            "create_lead otra vez para lo mismo; un asesor de ventas le dará seguimiento de precio "
            "y cobertura. Si insiste en precios, recuérdale con amabilidad que el asesor lo "
            "contactará. PERO si ahora te plantea OTRA cosa (una FALLA de un servicio que ya tiene, "
            "o un tema de cuenta/pago), atiéndela con normalidad según su carril (soporte / "
            "administración)."
        )
    messages = [{"role": "system", "content": system}]
    messages += state.get_history(conv_id, config.HISTORY_LIMIT)
    raw = llm.chat_completion(messages, json_mode=True)
    data = _parse_llm(raw)
    if data and data.get("action"):
        return data
    # El JSON no parseó (malformado/truncado o un '{' degenerado). NUNCA reenviar el
    # crudo al cliente: rescata el texto de `message` si está, y si no, fallback seguro.
    salvaged = _salvage_message(raw)
    if salvaged:
        logger.warning("conv %s: JSON LLM no parseable; rescatado message", conv_id)
        return {"action": "reply", "message": salvaged}
    logger.warning("conv %s: respuesta LLM no usable (%r); fallback", conv_id, (raw or "")[:80])
    return {"action": "reply", "message": MSG_LLM_FALLBACK}


def _create_order(d: dict, partner, decision: dict) -> dict | None:
    """Crea la orden con todo lo que juntó el bot: problema + servicio/domicilio
    reportado, horario de contacto y teléfono alterno; liga la sub y su domicilio."""
    summary = decision.get("summary") or d["content"]
    contact_time = (decision.get("contact_time") or "").strip()

    # ── NO verificado (número no encontrado en Odoo): reporte interno VERIFICAR IDENTIDAD ──
    # Datos DECLARADOS por el cliente, sin verificar. NO se liga a ninguna cuenta.
    if not partner:
        holder = (decision.get("account_holder") or "").strip()
        svc_addr = (decision.get("service_address") or "").strip()
        contact = (decision.get("alt_phone") or "").strip()
        lines = ["⚠ VERIFICAR IDENTIDAD — número NO registrado; datos DECLARADOS por el cliente, SIN verificar."]
        if holder:
            lines.append(f"Titular declarado: {holder}")
        if svc_addr:
            lines.append(f"Dirección de servicio declarada: {svc_addr}")
        if contact:
            lines.append(f"Contacto declarado: {contact}")
        if contact_time:
            lines.append(f"Horario de contacto: {contact_time}")
        lines += ["---", summary]
        return odoo.create_reconcile_fsm_order(d["phone"], "\n".join(lines), d["name"])

    # ── Verificado: liga la suscripción y su domicilio ──
    sub_name = (decision.get("subscription") or "").strip()
    alt_phone = (decision.get("alt_phone") or "").strip()
    extras = []
    if sub_name:
        extras.append(f"Servicio/domicilio reportado: {sub_name}")
    if contact_time:
        extras.append(f"Horario de contacto preferido: {contact_time}")
    if alt_phone:
        extras.append(f"Teléfono alterno: {alt_phone}")
    body = ("\n".join(extras) + "\n---\n" + summary) if extras else summary

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


def _create_lead(d: dict, partner, decision: dict) -> dict | None:
    """Crea una oportunidad CRM de ventas con lo que juntó el bot (qué quiere + zona +
    contacto), asignada al equipo/vendedor de ventas. Sirve para prospectos nuevos
    (sin cuenta) y para clientes existentes que quieren ampliar/contratar."""
    interest = (decision.get("interest") or "").strip()
    summary = (decision.get("summary") or d["content"]).strip()
    alt_phone = (decision.get("alt_phone") or "").strip()
    pname = (decision.get("prospect_name") or "").strip() or d.get("name") or ""

    if partner:
        contact_name = partner.get("name") or pname
        title = f"{partner.get('name','Cliente')} — {interest or 'servicio nuevo'} (WhatsApp)"
        email = partner.get("email") or ""
    else:
        contact_name = pname
        title = f"Prospecto WhatsApp — {interest}" if interest else "Prospecto WhatsApp"
        email = ""

    lines = [f"Prospecto/solicitud vía WhatsApp (tel: {d['phone']})."]
    if not partner:
        lines.append("⚠ Número NO registrado en Odoo (prospecto nuevo).")
    if interest:
        lines.append(f"Interés: {interest}")
    if alt_phone:
        lines.append(f"Teléfono de contacto: {alt_phone}")
    if pname and not partner:
        lines.append(f"Nombre declarado: {pname}")
    lines += ["---", summary]

    return odoo.create_crm_lead(
        name=title,
        description="\n".join(lines),
        contact_name=contact_name,
        phone=alt_phone or d["phone"],
        email=email,
        partner_id=(partner["id"] if partner else None),
        team_id=config.CRM_VENTAS_TEAM_ID,
        user_id=config.CRM_VENTAS_USER_ID,
    )


def _attach_pending_photos(conv_id: int, order_id: int):
    """Descarga las fotos que mandó el cliente (de Chatwoot, por el host interno) y
    las adjunta a la orden FSM. Tolerante a fallos: nunca rompe la creación de la orden."""
    urls = state.get_photos(conv_id)
    for i, url in enumerate(urls, 1):
        try:
            internal = url.replace(config.CHATWOOT_PUBLIC_URL, config.CHATWOOT_BASE_URL)
            r = httpx.get(internal, timeout=25.0, follow_redirects=True)
            if r.status_code >= 300 or not r.content:
                logger.error("foto conv %s HTTP %s", conv_id, r.status_code)
                continue
            mime = (r.headers.get("content-type") or "image/jpeg").split(";")[0]
            ext = "png" if "png" in mime else ("pdf" if "pdf" in mime else "jpg")
            b64 = base64.b64encode(r.content).decode()
            if odoo.attach_image_to_order(order_id, b64, f"reporte_{order_id}_{i}.{ext}", mime):
                logger.info("conv %s: foto %s adjuntada a la orden %s", conv_id, i, order_id)
        except Exception as e:
            logger.error("conv %s: adjuntar foto error: %s", conv_id, e)
    state.clear_photos(conv_id)


# ── Ruteo por tema ──────────────────────────────────────────────────
_TOPIC_KW = {
    "cobranza": ["pago", "pagar", "adeudo", "debo", "cobr", "suspendid", "corte", "deuda", "recibo"],
    "facturacion": ["factura", "cfdi", "fiscal", "timbr", "complemento"],
    "ventas": ["contratar", "cotiz", "precio", "nuevo servicio", "quiero internet", "dar de alta"],
}


def _guess_topic(content: str) -> str:
    """Clasificador por palabra clave (para el escape duro a humano, sin LLM)."""
    c = content.lower()
    for topic, kws in _TOPIC_KW.items():
        if any(k in c for k in kws):
            return topic
    return config.DEFAULT_TOPIC


def _route_for(topic: str | None) -> dict:
    return config.ROUTING.get(topic or config.DEFAULT_TOPIC, config.ROUTING[config.DEFAULT_TOPIC])


def _assign_route(conv_id: int, topic: str | None) -> dict:
    """Asigna la conversación al equipo + agente del tema (el agente recibe la
    notificación email/push). NO cambia el status ni manda mensaje."""
    route = _route_for(topic)
    chatwoot.assign_team(conv_id, route["team"])
    if route.get("assignee"):
        chatwoot.assign_agent(conv_id, route["assignee"])
    return route


def _handoff_message(topic: str | None) -> str:
    """Mensaje de handoff honesto según el horario, nombrando el área."""
    area = AREA_NAMES.get(topic or config.DEFAULT_TOPIC, "un asesor")
    if _office_hours_now():
        return MSG_HANDOFF_OFFICE.format(area=area)
    return MSG_HANDOFF_AFTERHOURS.format(area=area, hours=config.OFFICE_HOURS_TEXT, when=_next_office_open())


def _do_handoff(conv_id: int, topic: str | None = None):
    topic = topic or config.DEFAULT_TOPIC
    route = _assign_route(conv_id, topic)
    chatwoot.send_message(conv_id, _handoff_message(topic))
    chatwoot.toggle_status(conv_id, "open")
    _handled.add(conv_id)
    logger.info("conv %s: handoff topic=%s team=%s assignee=%s",
                conv_id, topic, route["team"], route.get("assignee"))


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

    # Si mandó fotos, guárdalas para adjuntarlas a la orden cuando se cree.
    for url in d["image_urls"]:
        state.add_photo(conv_id, url)

    # Atajo duro: el cliente SIEMPRE puede escapar a un humano, pase lo que pase el LLM.
    if _wants_human(content):
        _do_handoff(conv_id, _guess_topic(content))
        return

    # Contexto del cliente (Odoo) + decisión del LLM. Si ya hay folio, el bot sigue
    # activo para follow-ups (no creó handoff al crear el ticket).
    existing_folio = state.get_order(conv_id)
    existing_lead = state.get_lead(conv_id)
    partner, ficha, name = _resolve_client(d["phone"])
    decision = _llm_decide(conv_id, name, ficha, existing_folio,
                           verified=bool(partner), lead_ref=existing_lead)
    action = (decision.get("action") or "reply").lower()
    message = decision.get("message") or ""
    topic = (decision.get("topic") or config.DEFAULT_TOPIC).lower()

    # ── CREATE_LEAD (ventas: registra la oportunidad y rutea a un vendedor) ──
    if action == "create_lead":
        if existing_lead:  # ya se registró un lead en esta conversación; no duplicar
            reply = message or "Tu solicitud ya quedó registrada; un asesor de ventas te contactará. 🙌"
            chatwoot.send_message(conv_id, reply)
            state.add_message(conv_id, "assistant", reply)
            return
        res = _create_lead(d, partner, decision)
        if not res or not res.get("ok"):
            logger.error("conv %s: fallo al crear lead CRM", conv_id)
            chatwoot.send_message(conv_id, MSG_ERROR_LEAD)
            _do_handoff(conv_id, "ventas")
            return
        state.set_lead(conv_id, f"LEAD-{res['id']}")  # anti-duplicado (slot propio del lead)
        greet = f" {name}" if name else ""
        tmpl = MSG_LEAD_OFFICE if _office_hours_now() else MSG_LEAD_AFTERHOURS
        lead_msg = tmpl.format(name=greet, hours=config.OFFICE_HOURS_TEXT, when=_next_office_open())
        chatwoot.send_message(conv_id, lead_msg)
        state.add_message(conv_id, "assistant", lead_msg)
        _post_lead_note(conv_id, d, partner, decision)
        # Rutea a ventas (equipo + vendedor, para que le llegue la notificación) pero NO
        # suelta a humano: igual que soporte, el bot queda en 'pending' y sigue activo
        # (puede atender follow-ups o si el cliente pivota a una falla). El vendedor toma
        # la conversación al responder (ahí Chatwoot la pasa a 'open' y el bot calla).
        route = _assign_route(conv_id, "ventas")
        logger.info("conv %s: lead %s creado (match=%s) → ventas team=%s assignee=%s; bot sigue activo",
                    conv_id, res.get("name"), bool(partner), route["team"], route.get("assignee"))
        return

    # ── HANDOFF (sí suelta a humano: cliente lo pide o el bot no puede resolver) ──
    if action == "handoff":
        # Para temas administrativos de un cliente identificado, deja la ficha como nota
        # interna para quien lo atienda (cobranza/facturación → Irma).
        if partner and topic in ("cobranza", "facturacion"):
            _post_client_note(conv_id, d["phone"])
        _do_handoff(conv_id, topic)
        logger.info("conv %s: handoff (IA) topic=%s", conv_id, topic)
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
            _do_handoff(conv_id)
            return
        folio = res["name"]
        state.set_order(conv_id, folio)
        greet = f" {name}" if name else ""
        tmpl = MSG_FOLIO_OFFICE if _office_hours_now() else MSG_FOLIO_AFTERHOURS
        folio_msg = tmpl.format(name=greet, folio=folio,
                                hours=config.OFFICE_HOURS_TEXT, when=_next_office_open())
        chatwoot.send_message(conv_id, folio_msg)
        state.add_message(conv_id, "assistant", folio_msg)
        _attach_pending_photos(conv_id, res["id"])
        _post_client_note(conv_id, d["phone"])
        # Asigna a soporte (equipo + agente, para que le llegue la notificación), pero
        # NO suelta a humano: la conversación queda en 'pending' y el bot sigue los follow-ups.
        _assign_route(conv_id, "soporte")
        logger.info("conv %s: orden %s creada (match=%s); bot sigue activo", conv_id, folio, bool(partner))
        return

    # ── REPLY (default) ──
    reply = message or MSG_LLM_FALLBACK
    chatwoot.send_message(conv_id, reply)
    state.add_message(conv_id, "assistant", reply)


def _post_lead_note(conv_id: int, d: dict, partner, decision: dict):
    """Nota interna para el vendedor con el resumen del prospecto/solicitud."""
    interest = (decision.get("interest") or "").strip()
    summary = (decision.get("summary") or "").strip()
    alt_phone = (decision.get("alt_phone") or "").strip()
    pname = (decision.get("prospect_name") or "").strip() or d.get("name") or ""
    lines = ["🟢 *Oportunidad de ventas (WhatsApp)*"]
    if partner:
        lines.append(f"Cliente Odoo: {partner.get('name','')}")
    else:
        lines.append("⚠ Número NO registrado (prospecto nuevo).")
        if pname:
            lines.append(f"Nombre declarado: {pname}")
    if interest:
        lines.append(f"Interés: {interest}")
    lines.append(f"Teléfono WhatsApp: {d['phone']}")
    if alt_phone:
        lines.append(f"Tel. contacto: {alt_phone}")
    if summary:
        lines.append(f"Solicita: {summary}")
    chatwoot.send_message(conv_id, "\n".join(lines), private=True)


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

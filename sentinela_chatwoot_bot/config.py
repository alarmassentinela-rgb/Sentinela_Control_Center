"""Configuración por variables de entorno del bot de reportes (AgentBot Chatwoot)."""

import os
from zoneinfo import ZoneInfo

# ── Chatwoot ───────────────────────────────────────────────────────
# URL interna del rails de Chatwoot (alias de red docker, NO el dominio público).
CHATWOOT_BASE_URL = os.environ.get("CHATWOOT_BASE_URL", "http://rails:3000")
CHATWOOT_ACCOUNT_ID = int(os.environ.get("CHATWOOT_ACCOUNT_ID", "1"))
# Token de acceso del AgentBot (se obtiene al crear el bot en Chatwoot).
CHATWOOT_BOT_TOKEN = os.environ.get("CHATWOOT_BOT_TOKEN", "")
# Inbox que atiende este bot; 0 = no filtrar por inbox.
CHATWOOT_INBOX_ID = int(os.environ.get("CHATWOOT_INBOX_ID", "1"))

# ── Handoff a humanos ──────────────────────────────────────────────
# Team al que se asigna la conversación cuando el bot termina el intake o el
# cliente pide asesor (2 = soporte, según teams de Chatwoot).
HANDOFF_TEAM_ID = int(os.environ.get("HANDOFF_TEAM_ID", "2"))
HANDOFF_KEYWORDS = [
    w.strip().lower() for w in os.environ.get(
        "HANDOFF_KEYWORDS",
        "asesor,humano,persona,ejecutivo,agente,representante,operador"
    ).split(",") if w.strip()
]

# ── Horario de oficina (atención humana) ───────────────────────────
TZ = ZoneInfo(os.environ.get("TZ", "America/Mexico_City"))
OFFICE_START = int(os.environ.get("OFFICE_START", "9"))   # hora inicio (24h)
OFFICE_END = int(os.environ.get("OFFICE_END", "18"))      # hora fin (24h)
# Días hábiles: lunes=0 ... domingo=6. Default L-V.
OFFICE_DAYS = [int(d) for d in os.environ.get("OFFICE_DAYS", "0,1,2,3,4").split(",") if d.strip()]

# ── Idempotencia ───────────────────────────────────────────────────
# Etiqueta que marca que ya se levantó el reporte en esta conversación.
INTAKE_LABEL = os.environ.get("INTAKE_LABEL", "reporte-registrado")

# ── Odoo ───────────────────────────────────────────────────────────
# odoo.py lee ODOO_URL / ODOO_DB / ODOO_USER / ODOO_PASSWORD directo de os.environ.
ODOO_URL = os.environ.get("ODOO_URL", "")

# ── LLM (OpenRouter) ───────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# ── Estado / historial ─────────────────────────────────────────────
STATE_DB_PATH = os.environ.get("STATE_DB_PATH", "/data/state.db")
HISTORY_LIMIT = int(os.environ.get("HISTORY_LIMIT", "14"))  # turnos que se mandan al LLM

# ── System prompt del asistente ────────────────────────────────────
# {name} = nombre del cliente (o vacío) · {ficha} = contexto Odoo (o "Cliente no identificado")
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT", """\
Eres el asistente virtual de *Sentinela*, empresa de Matamoros, México que da servicios de \
seguridad/alarmas, internet (WISP) y rastreo GPS. Atiendes el WhatsApp de REPORTES de fallas. \
Tu trabajo es recibir el reporte de falla de un cliente y, cuando tengas la información suficiente, \
levantar una orden de servicio.

Cómo debes comportarte:
- Saluda cálido y breve. Español de México, tono amable y profesional. Mensajes CORTOS (2-3 líneas máx). \
Usa el nombre del cliente si lo conoces: {name}
- Tu meta es entender QUÉ falla tiene y DESDE CUÁNDO, con detalle suficiente para que un técnico actúe \
(p.ej. para internet: luces del módem; para alarma: qué zona/sensor; para GPS: qué unidad).
- Haz UNA pregunta a la vez. No abrumes.
- NUNCA inventes folios, datos, ni soluciones técnicas; no prometas tiempos exactos de llegada.
- Cuando ya tengas una descripción CLARA del problema, RESUME el problema en una frase y pide al cliente \
que confirme que levantes el reporte (ej. "¿Confirmas que levante el reporte de ...?").
- SOLO cuando el cliente confirme, usa la acción create_ticket. En el `summary` incluye \
ÚNICAMENTE lo que el cliente realmente dijo; NO agregues síntomas, colores de luces ni \
detalles que él no haya mencionado.
- Si el cliente solo saluda o manda algo sin contenido ("hola", "sí", "ok", "gracias"), pregúntale \
amablemente qué problema tiene. NO levantes reporte por mensajes sin contenido.
- Si te avisan que el cliente envió un archivo adjunto (foto/audio) sin texto, agradécelo y pídele \
que te describa el problema POR ESCRITO (todavía no puedes ver fotos ni oír audios).
- Si el cliente pide hablar con una persona, está muy molesto, o su tema NO es un reporte de falla \
(ventas, cobranza/pagos, dudas comerciales complejas), usa la acción handoff.

Contexto del cliente (de nuestro sistema Odoo):
{ficha}

Responde SIEMPRE con UN único JSON válido y NADA de texto fuera del JSON:
{{"action": "reply" | "create_ticket" | "handoff", "message": "<lo que le dices al cliente>", "summary": "<solo si create_ticket: el problema resumido para la orden>"}}\
""")

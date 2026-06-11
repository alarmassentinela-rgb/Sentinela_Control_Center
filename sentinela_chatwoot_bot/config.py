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

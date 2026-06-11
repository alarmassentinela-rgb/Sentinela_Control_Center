"""Cliente mínimo de la API de Chatwoot, autenticado como el AgentBot.

El AgentBot usa su propio access_token (header `api_access_token`). Con él puede
responder en la conversación, etiquetarla, asignar team y cambiar su estado.
"""

import logging

import httpx

import config

logger = logging.getLogger("chatwoot_bot.chatwoot")

_TIMEOUT = 15.0


def _base() -> str:
    return f"{config.CHATWOOT_BASE_URL}/api/v1/accounts/{config.CHATWOOT_ACCOUNT_ID}"


def _headers() -> dict:
    return {"api_access_token": config.CHATWOOT_BOT_TOKEN,
            "Content-Type": "application/json"}


def _post(path: str, payload: dict) -> bool:
    try:
        r = httpx.post(f"{_base()}{path}", json=payload, headers=_headers(), timeout=_TIMEOUT)
        if r.status_code >= 300:
            logger.error("Chatwoot POST %s → %s %s", path, r.status_code, r.text[:300])
            return False
        return True
    except Exception as e:
        logger.error("Chatwoot POST %s error: %s", path, e)
        return False


def send_message(conversation_id: int, content: str, private: bool = False) -> bool:
    """Envía un mensaje a la conversación. private=True → nota interna (solo agentes)."""
    return _post(f"/conversations/{conversation_id}/messages", {
        "content": content,
        "message_type": "outgoing",
        "private": private,
    })


def add_labels(conversation_id: int, labels: list[str]) -> bool:
    """Reemplaza las etiquetas de la conversación (Chatwoot no tiene 'append')."""
    return _post(f"/conversations/{conversation_id}/labels", {"labels": labels})


def assign_team(conversation_id: int, team_id: int) -> bool:
    return _post(f"/conversations/{conversation_id}/assignments", {"team_id": team_id})


def toggle_status(conversation_id: int, status: str = "open") -> bool:
    return _post(f"/conversations/{conversation_id}/toggle_status", {"status": status})


def get_conversation(conversation_id: int) -> dict | None:
    """Lee la conversación (estado + etiquetas actuales) como fallback de idempotencia."""
    try:
        r = httpx.get(f"{_base()}/conversations/{conversation_id}",
                      headers=_headers(), timeout=_TIMEOUT)
        if r.status_code >= 300:
            logger.error("Chatwoot GET conv %s → %s", conversation_id, r.status_code)
            return None
        return r.json()
    except Exception as e:
        logger.error("Chatwoot GET conv %s error: %s", conversation_id, e)
        return None

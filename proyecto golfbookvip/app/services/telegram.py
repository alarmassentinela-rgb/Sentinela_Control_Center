"""Telegram Bot API client para GolfBookVIP. v1.21.0.

Llama directamente a `api.telegram.org/bot<TOKEN>/sendMessage`. Sin
dependencias adicionales: usa httpx (ya en requirements).

Si TELEGRAM_BOT_TOKEN no está configurado, los envíos loggean warning y
retornan False sin lanzar — mismo patrón que mailer.py.
"""
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("golfbookvip.telegram")

_API_BASE = "https://api.telegram.org"


def is_configured() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN)


async def send_telegram(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Envía mensaje al chat_id vía Bot API. Retorna True si OK, False si no
    configurado o error. NUNCA lanza."""
    if not is_configured():
        logger.warning(f"TELEGRAM_BOT_TOKEN no configurado; skip mensaje a {chat_id}")
        return False
    if not chat_id:
        logger.warning("chat_id vacío; skip")
        return False
    url = f"{_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": str(chat_id),
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
        if r.is_success:
            logger.info(f"Telegram enviado a chat_id={chat_id}")
            return True
        logger.error(f"Telegram error {r.status_code} a chat_id={chat_id}: {r.text}")
        return False
    except Exception as e:
        logger.error(f"Telegram excepción a chat_id={chat_id}: {e}")
        return False


async def get_me() -> Optional[dict]:
    """Devuelve info del bot (debug). None si no configurado."""
    if not is_configured():
        return None
    url = f"{_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url)
        return r.json() if r.is_success else None
    except Exception:
        return None


async def set_webhook(webhook_url: str) -> bool:
    """Registra el webhook (idempotente). Llamar una vez por deploy/dominio."""
    if not is_configured():
        return False
    url = f"{_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, json={"url": webhook_url, "allowed_updates": ["message"]})
        return r.is_success
    except Exception:
        return False


# Lista de comandos del bot (v1.22). El autocompletado en los clientes Telegram
# se actualiza llamando set_my_commands() al deploy.
BOT_COMMANDS = [
    {"command": "saldo",     "description": "Tu balance en cada club"},
    {"command": "proxima",   "description": "Tu próxima reserva"},
    {"command": "reservas",  "description": "Tus próximas reservas"},
    {"command": "handicap",  "description": "Tu hándicap actual"},
    {"command": "cuenta",    "description": "Resumen de tu cuenta"},
    {"command": "help",      "description": "Ayuda"},
]


async def set_my_commands(commands: Optional[list[dict]] = None) -> bool:
    """Registra los comandos disponibles en BotFather (autocomplete en clients)."""
    if not is_configured():
        return False
    cmds = commands if commands is not None else BOT_COMMANDS
    url = f"{_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/setMyCommands"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, json={"commands": cmds})
        if r.is_success:
            logger.info(f"setMyCommands OK ({len(cmds)} comandos)")
            return True
        logger.error(f"setMyCommands error {r.status_code}: {r.text}")
        return False
    except Exception as e:
        logger.error(f"setMyCommands excepción: {e}")
        return False

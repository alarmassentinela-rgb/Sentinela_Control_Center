"""Webhook de Telegram. v1.21.0.

Recibe actualizaciones del bot @GolfBookVip_bot. La ruta tiene un path-secret
para que solo Telegram (que conoce el webhook URL) pueda llamar.

Flujo principal: el usuario envía `/start <token>` al bot tras generarlo
desde su perfil; el webhook lo recibe, busca el token, vincula el chat_id
con el user, y responde con confirmación.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import DB
from app.models.telegram import TelegramLinkToken
from app.models.user import User
from app.services.telegram import send_telegram
from app.services.telegram_templates import tg_account_linked, tg_link_invalid
from app.services.telegram_handlers import get_command_handler, cmd_unknown, cmd_help

logger = logging.getLogger("golfbookvip.telegram.webhook")
router = APIRouter()


class _TGUser(BaseModel):
    id: int
    is_bot: Optional[bool] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None


class _TGChat(BaseModel):
    id: int
    type: Optional[str] = None
    username: Optional[str] = None


class _TGMessage(BaseModel):
    message_id: int
    from_: Optional[_TGUser] = None
    chat: _TGChat
    text: Optional[str] = None

    model_config = {"populate_by_name": True}


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[dict] = None  # parseamos manual para evitar issues con `from`


@router.post("/webhook/{secret}")
async def telegram_webhook(secret: str, update: dict, db: DB):
    """Recibe updates del bot. El path-secret previene llamadas no autorizadas."""
    if not settings.TELEGRAM_WEBHOOK_SECRET or secret != settings.TELEGRAM_WEBHOOK_SECRET:
        # No revelar 401/403 a sondas externas — Telegram retry forever si 5xx,
        # pero un 200 vacío descarta y no genera reintentos.
        logger.warning(f"Webhook con secret inválido")
        return {"ok": True}

    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return {"ok": True}

    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    from_user = message.get("from") or {}
    tg_username = from_user.get("username")
    text = (message.get("text") or "").strip()

    if not chat_id:
        return {"ok": True}

    # Procesamos /start [token]
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        token_arg = parts[1].strip() if len(parts) > 1 else ""

        if token_arg:
            # Flujo de vinculación con token
            tk_res = await db.execute(
                select(TelegramLinkToken).where(TelegramLinkToken.token == token_arg)
            )
            link_tk = tk_res.scalar_one_or_none()

            if not link_tk:
                await send_telegram(chat_id, tg_link_invalid())
                return {"ok": True}

            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            if link_tk.used_at is not None:
                await send_telegram(chat_id, tg_link_invalid())
                return {"ok": True}
            created_at = link_tk.created_at
            if created_at and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if created_at and created_at < cutoff:
                await send_telegram(chat_id, tg_link_invalid())
                return {"ok": True}

            u_res = await db.execute(select(User).where(User.id == link_tk.user_id))
            user = u_res.scalar_one_or_none()
            if not user:
                await send_telegram(chat_id, tg_link_invalid())
                return {"ok": True}

            user.telegram_chat_id = chat_id
            user.telegram_username = tg_username
            link_tk.used_at = datetime.now(timezone.utc)
            await db.flush()

            await send_telegram(chat_id, tg_account_linked())
            logger.info(f"Telegram vinculado: user_id={user.id} chat_id={chat_id} username=@{tg_username}")
            return {"ok": True}

        # /start sin token — equivalente a /help, requiere que la cuenta esté vinculada
        # Si no está vinculada, mensaje de invitación a vincular
        u_res = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = u_res.scalar_one_or_none()
        if not user:
            await send_telegram(chat_id, (
                "👋 Hola, soy <b>GolfBookVIP Bot</b>.\n\n"
                "Para vincular tu cuenta y recibir notificaciones, ve a tu perfil "
                "en <a href=\"https://golfbookvip.com/es/profile\">golfbookvip.com</a> "
                "y haz clic en \"Conectar mi Telegram\"."
            ))
            return {"ok": True}
        await send_telegram(chat_id, await cmd_help(db, user))
        return {"ok": True}

    # Cualquier otro comando: identificar al usuario por chat_id
    if text.startswith("/"):
        u_res = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = u_res.scalar_one_or_none()
        if not user:
            await send_telegram(chat_id, (
                "🔒 Esta cuenta de Telegram no está vinculada a ningún usuario de GolfBookVIP.\n\n"
                "Ve a tu perfil en <a href=\"https://golfbookvip.com/es/profile\">golfbookvip.com</a> "
                "y haz clic en \"Conectar mi Telegram\"."
            ))
            return {"ok": True}

        handler = get_command_handler(text)
        if handler is None:
            response = await cmd_unknown(db, user)
        else:
            try:
                response = await handler(db, user)
            except Exception as e:
                logger.exception(f"Error en comando {text}: {e}")
                response = "⚠️ Ocurrió un error procesando tu solicitud. Inténtalo de nuevo en un momento."
        await send_telegram(chat_id, response)
        return {"ok": True}

    # Mensajes que no son comandos — ignorar silenciosamente (v1.22 es solo comandos)
    return {"ok": True}

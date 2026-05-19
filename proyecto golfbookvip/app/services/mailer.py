"""Mailer genérico para GolfBookVIP. Usa fastapi-mail (ya en requirements).

Si SMTP no está configurado (MAIL_USERNAME/PASSWORD vacíos), las llamadas
loggean warning y retornan False — diseñado para fire-and-forget desde
FastAPI BackgroundTasks sin romper el flujo del endpoint que las invoca.
"""
import logging
from typing import Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

from app.core.config import settings

logger = logging.getLogger("golfbookvip.mailer")


def _is_smtp_configured() -> bool:
    return bool(settings.MAIL_USERNAME and settings.MAIL_PASSWORD)


def _get_conf() -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
        TIMEOUT=settings.MAIL_TIMEOUT,
    )


async def send_email(to_email: str, subject: str, html_body: str,
                       text_body: Optional[str] = None) -> bool:
    """Envía un email. Retorna True si se envió, False si SMTP no estaba configurado
    o hubo error. NUNCA lanza excepción — el caller no debe depender del envío."""
    if not _is_smtp_configured():
        logger.warning(f"SMTP no configurado; skip email a {to_email}: {subject}")
        return False

    if not to_email or "@" not in to_email:
        logger.warning(f"Email destino inválido; skip: {to_email}")
        return False

    try:
        message = MessageSchema(
            subject=subject,
            recipients=[to_email],
            body=html_body,
            subtype=MessageType.html,
        )
        fm = FastMail(_get_conf())
        await fm.send_message(message)
        logger.info(f"Email enviado a {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Error enviando email a {to_email}: {e}")
        return False

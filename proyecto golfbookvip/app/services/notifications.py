"""Helper para crear notificaciones in-app + email.

`push()` (legacy): solo crea Notification row in-app. Sigue siendo usado por endpoints
de rondas que prefieren manejar el email aparte.

`notify_user()` (v1.20+): unificado. Lee preferencias del usuario, crea in-app si
notify_inapp=True, y agenda email async via BackgroundTasks si notify_email=True
y se pasaron subject+html.
"""
import logging
import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import select

from app.models.notification import Notification
from app.models.user import User
from app.services.mailer import send_email

if TYPE_CHECKING:
    from fastapi import BackgroundTasks

logger = logging.getLogger("golfbookvip.notifications")


async def push(
    db,
    user_id: uuid.UUID,
    type_: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> None:
    """Agrega una notificación in-app a la sesión de DB (se persiste en el commit del request).
    Helper legacy — no envía email. Para nuevos flujos usar notify_user()."""
    db.add(Notification(
        user_id=user_id,
        type=type_,
        title=title,
        body=body,
        data=data or {},
    ))


async def notify_user(
    db,
    user_id: uuid.UUID,
    type_: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
    email_subject: Optional[str] = None,
    email_html: Optional[str] = None,
    background_tasks: Optional["BackgroundTasks"] = None,
) -> None:
    """Notificación unificada in-app + email. Lee preferencias del user.

    - Si user.notify_inapp → crea Notification row (in-app, bell counter).
    - Si user.notify_email + email_subject + email_html → agenda envío via
      BackgroundTasks (no bloquea la respuesta del endpoint).

    Si background_tasks no se pasa, el email se envía sincrónicamente al final
    de la corutina (útil para cron jobs / scripts donde no hay request).
    """
    # Cargar user para preferencias y email
    u_res = await db.execute(select(User).where(User.id == user_id))
    user = u_res.scalar_one_or_none()
    if not user:
        logger.warning(f"notify_user: user_id {user_id} no existe; skip")
        return

    # 1) In-app
    if user.notify_inapp:
        db.add(Notification(
            user_id=user.id,
            type=type_,
            title=title,
            body=body,
            data=data or {},
        ))

    # 2) Email
    if email_subject and email_html and user.notify_email and user.email:
        if background_tasks is not None:
            background_tasks.add_task(send_email, user.email, email_subject, email_html)
        else:
            await send_email(user.email, email_subject, email_html)

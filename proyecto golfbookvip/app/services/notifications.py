"""Helper para crear notificaciones desde cualquier endpoint."""
import uuid
from typing import Optional
from app.models.notification import Notification


async def push(
    db,
    user_id: uuid.UUID,
    type_: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> None:
    """Agrega una notificación a la sesión de DB (se persiste en el commit del request)."""
    db.add(Notification(
        user_id=user_id,
        type=type_,
        title=title,
        body=body,
        data=data or {},
    ))

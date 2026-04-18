import uuid
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func, update
from app.core.deps import CurrentUser, DB
from app.models.notification import Notification

router = APIRouter()


@router.get("/unread-count")
async def get_unread_count(current_user: CurrentUser, db: DB):
    count = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
    )
    return {"count": count or 0}


@router.get("")
async def list_notifications(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifications = result.scalars().all()
    return [
        {
            "id": str(n.id),
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "data": n.data,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]


@router.post("/{notif_id}/read", status_code=204)
async def mark_read(notif_id: uuid.UUID, current_user: CurrentUser, db: DB):
    notif = await db.scalar(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.user_id == current_user.id,
        )
    )
    if not notif:
        raise HTTPException(404, "Notificación no encontrada")
    notif.is_read = True
    db.add(notif)


@router.post("/read-all", status_code=204)
async def mark_all_read(current_user: CurrentUser, db: DB):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
        .values(is_read=True)
    )

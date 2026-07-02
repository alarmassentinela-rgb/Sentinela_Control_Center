from fastapi import APIRouter
from app.api.v1 import auth, users, clubs, courses, rounds, scores_ws, stripe_webhook, groups, notifications, chat, admin, telegram, uploads, billing

api_router = APIRouter()

api_router.include_router(auth.router,             prefix="/auth",          tags=["auth"])
api_router.include_router(users.router,            prefix="/users",         tags=["users"])
api_router.include_router(clubs.router,            prefix="/clubs",         tags=["clubs"])
api_router.include_router(courses.router,          prefix="/courses",       tags=["courses"])
api_router.include_router(rounds.router,           prefix="/rounds",        tags=["rounds"])
api_router.include_router(groups.router,           prefix="/groups",        tags=["groups"])
api_router.include_router(notifications.router,    prefix="/notifications", tags=["notifications"])
api_router.include_router(chat.router,             prefix="/chat",          tags=["chat"])
api_router.include_router(scores_ws.router,        prefix="/ws",            tags=["websocket"])
api_router.include_router(stripe_webhook.router,   prefix="/stripe",        tags=["stripe"])
api_router.include_router(admin.router,            prefix="/admin",         tags=["admin"])
api_router.include_router(telegram.router,         prefix="/telegram",      tags=["telegram"])
api_router.include_router(uploads.router,          prefix="/uploads",       tags=["uploads"])
api_router.include_router(billing.router,          prefix="/billing",       tags=["billing"])

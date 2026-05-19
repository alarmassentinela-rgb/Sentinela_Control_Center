"""Super-admin dashboard API — restricted to users with is_superadmin=True."""
from fastapi import APIRouter, HTTPException, Header
from sqlalchemy import select, func, case, text, and_
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from typing import Optional

from app.core.deps import CurrentUser, DB
from app.core.config import settings
from app.core.security import create_reset_token
from app.models.user import User
from app.models.round import Round, RoundPlayer
from app.models.score import Score
from app.models.course import Course
from app.models.handicap import ScoreDifferential
from app.services.notifications import notify_user
from app.services.email_templates import tpl_tee_time_reminder
from app.services.telegram_templates import tg_tee_time_reminder

router = APIRouter()


class UserPatchPayload(BaseModel):
    handicap_index: Optional[float] = Field(default=None, ge=-10, le=54)


def _require_admin(current_user: User):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Acceso restringido a superadministradores")


# ─── Stats overview ──────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(current_user: CurrentUser, db: DB):
    _require_admin(current_user)

    now = datetime.now(timezone.utc)
    day7  = now - timedelta(days=7)
    day30 = now - timedelta(days=30)

    # Users
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
    new_7d      = (await db.execute(select(func.count()).select_from(User).where(User.created_at >= day7))).scalar()
    new_30d     = (await db.execute(select(func.count()).select_from(User).where(User.created_at >= day30))).scalar()
    active_30d  = (await db.execute(select(func.count()).select_from(User).where(User.last_login >= day30))).scalar()
    with_hcp    = (await db.execute(select(func.count()).select_from(User).where(User.handicap_index.isnot(None)))).scalar()

    # Rounds
    total_rounds    = (await db.execute(select(func.count()).select_from(Round))).scalar()
    rounds_sched    = (await db.execute(select(func.count()).select_from(Round).where(Round.status == 'scheduled'))).scalar()
    rounds_active   = (await db.execute(select(func.count()).select_from(Round).where(Round.status == 'active'))).scalar()
    rounds_finished = (await db.execute(select(func.count()).select_from(Round).where(Round.status == 'finished'))).scalar()
    rounds_7d       = (await db.execute(select(func.count()).select_from(Round).where(Round.created_at >= day7))).scalar()
    rounds_30d      = (await db.execute(select(func.count()).select_from(Round).where(Round.created_at >= day30))).scalar()

    # Rounds by format
    fmt_res = await db.execute(
        select(Round.game_format, func.count().label("n"))
        .group_by(Round.game_format)
        .order_by(func.count().desc())
    )
    formats = [{"format": r.game_format, "count": r.n} for r in fmt_res.all()]

    # Players (participaciones)
    total_players = (await db.execute(select(func.count()).select_from(RoundPlayer))).scalar()

    # Scores
    total_scores = (await db.execute(select(func.count()).select_from(Score))).scalar()

    # Courses & differentials
    total_courses = (await db.execute(select(func.count()).select_from(Course).where(Course.is_active == True))).scalar()
    total_diffs   = (await db.execute(select(func.count()).select_from(ScoreDifferential))).scalar()

    return {
        "users": {
            "total": total_users,
            "new_7d": new_7d,
            "new_30d": new_30d,
            "active_30d": active_30d,
            "with_handicap": with_hcp,
        },
        "rounds": {
            "total": total_rounds,
            "scheduled": rounds_sched,
            "active": rounds_active,
            "finished": rounds_finished,
            "new_7d": rounds_7d,
            "new_30d": rounds_30d,
            "by_format": formats,
        },
        "scores": {
            "total": total_scores,
            "differentials": total_diffs,
        },
        "participations": total_players,
        "courses_active": total_courses,
        "generated_at": now.isoformat(),
    }


# ─── Daily signups (last 30 days) ────────────────────────────────────────────

@router.get("/signups-chart")
async def get_signups_chart(current_user: CurrentUser, db: DB):
    _require_admin(current_user)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=29)

    result = await db.execute(
        select(
            func.date_trunc('day', User.created_at).label("day"),
            func.count().label("n"),
        )
        .where(User.created_at >= since)
        .group_by(func.date_trunc('day', User.created_at))
        .order_by(func.date_trunc('day', User.created_at))
    )
    return [{"day": r.day.date().isoformat(), "count": r.n} for r in result.all()]


# ─── Daily rounds created (last 30 days) ─────────────────────────────────────

@router.get("/rounds-chart")
async def get_rounds_chart(current_user: CurrentUser, db: DB):
    _require_admin(current_user)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=29)

    result = await db.execute(
        select(
            func.date_trunc('day', Round.created_at).label("day"),
            func.count().label("n"),
        )
        .where(Round.created_at >= since)
        .group_by(func.date_trunc('day', Round.created_at))
        .order_by(func.date_trunc('day', Round.created_at))
    )
    return [{"day": r.day.date().isoformat(), "count": r.n} for r in result.all()]


# ─── Recent users ─────────────────────────────────────────────────────────────

@router.get("/users")
async def get_users(current_user: CurrentUser, db: DB, page: int = 1, q: str = ""):
    _require_admin(current_user)
    limit = 20
    offset = (page - 1) * limit

    query = select(User).order_by(User.created_at.desc())
    count_query = select(func.count()).select_from(User)
    if q:
        like = f"%{q}%"
        query = query.where(
            (User.first_name.ilike(like)) |
            (User.last_name.ilike(like))  |
            (User.email.ilike(like))      |
            (User.username.ilike(like))
        )
        count_query = count_query.where(
            (User.first_name.ilike(like)) |
            (User.last_name.ilike(like))  |
            (User.email.ilike(like))      |
            (User.username.ilike(like))
        )

    total = (await db.execute(count_query)).scalar()
    users = (await db.execute(query.limit(limit).offset(offset))).scalars().all()

    return {
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "username": u.username,
                "handicap_index": float(u.handicap_index) if u.handicap_index else None,
                "is_active": u.is_active,
                "is_superadmin": u.is_superadmin,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
            for u in users
        ],
    }


# ─── Recent rounds ────────────────────────────────────────────────────────────

@router.get("/rounds")
async def get_rounds(current_user: CurrentUser, db: DB, page: int = 1):
    _require_admin(current_user)
    limit = 20
    offset = (page - 1) * limit

    result = await db.execute(
        select(Round, User)
        .outerjoin(User, User.id == Round.created_by)
        .order_by(Round.created_at.desc())
        .limit(limit).offset(offset)
    )
    rows = result.all()
    total = (await db.execute(select(func.count()).select_from(Round))).scalar()

    rounds_out = []
    for r, u in rows:
        player_count = (await db.execute(
            select(func.count()).select_from(RoundPlayer).where(RoundPlayer.round_id == r.id)
        )).scalar()
        rounds_out.append({
            "id": str(r.id),
            "name": r.name,
            "game_format": r.game_format,
            "status": r.status,
            "holes_to_play": r.holes_to_play,
            "player_count": player_count,
            "created_by_name": f"{u.first_name} {u.last_name}" if u else "—",
            "created_by_email": u.email if u else "—",
            "scheduled_at": r.scheduled_at.isoformat(),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "rounds": rounds_out,
    }


# ─── Top players by rounds ────────────────────────────────────────────────────

@router.get("/top-players")
async def get_top_players(current_user: CurrentUser, db: DB):
    _require_admin(current_user)
    result = await db.execute(
        select(User, func.count(RoundPlayer.id).label("rounds"))
        .join(RoundPlayer, RoundPlayer.user_id == User.id)
        .group_by(User.id)
        .order_by(func.count(RoundPlayer.id).desc())
        .limit(10)
    )
    return [
        {
            "user_id": str(u.id),
            "name": f"{u.first_name} {u.last_name}",
            "username": u.username,
            "handicap_index": float(u.handicap_index) if u.handicap_index else None,
            "rounds": rounds,
        }
        for u, rounds in result.all()
    ]


# ─── Toggle user active status ────────────────────────────────────────────────

@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(user_id: str, current_user: CurrentUser, db: DB):
    _require_admin(current_user)
    import uuid as _uuid
    result = await db.execute(select(User).where(User.id == _uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.is_superadmin:
        raise HTTPException(status_code=400, detail="No puedes desactivar a un superadmin")
    user.is_active = not user.is_active
    await db.flush()
    return {"user_id": user_id, "is_active": user.is_active}


# ─── Update user fields (handicap_index for now) ──────────────────────────────

@router.patch("/users/{user_id}")
async def update_user(user_id: str, payload: UserPatchPayload, current_user: CurrentUser, db: DB):
    _require_admin(current_user)
    import uuid as _uuid
    result = await db.execute(select(User).where(User.id == _uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.handicap_index = payload.handicap_index
    await db.flush()
    return {
        "user_id": user_id,
        "handicap_index": float(user.handicap_index) if user.handicap_index is not None else None,
    }


# ─── Generate password reset link for a user ──────────────────────────────────

@router.post("/users/{user_id}/reset-link")
async def generate_reset_link(user_id: str, current_user: CurrentUser, db: DB):
    """Superadmin genera un token de reset de 1h para un jugador.
    Devuelve el token; el frontend arma la URL completa con su origin + locale."""
    _require_admin(current_user)
    import uuid as _uuid
    result = await db.execute(select(User).where(User.id == _uuid.UUID(user_id), User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o inactivo")
    token = create_reset_token(str(user.id), user.password_hash)
    return {
        "user_id": user_id,
        "user_email": user.email,
        "user_name": f"{user.first_name} {user.last_name}",
        "token": token,
        "expires_in_hours": 1,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GOLFBOOKVIP CLUBS — Super admin manages SaaS golf clubs (tenants)
# ═══════════════════════════════════════════════════════════════════════════════

import re as _re
import uuid as _uuid
from datetime import date as _date
from app.models.club import Club, ClubStaff, ClubMember


class ClubCreatePayload(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "MX"
    phone: Optional[str] = None
    email: Optional[str] = None
    currency: str = "MXN"
    timezone: str = "America/Mexico_City"
    plan_id: Optional[int] = None
    admin_user_id: Optional[str] = None  # opcional: auto-asignar un admin del club


class ClubPatchPayload(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    plan_id: Optional[int] = None
    is_active: Optional[bool] = None


def _slugify(name: str) -> str:
    s = _re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or f"club-{_uuid.uuid4().hex[:8]}"


@router.get("/clubs")
async def list_all_clubs(current_user: CurrentUser, db: DB, q: str = "", include_inactive: bool = False):
    """Lista todos los clubes con conteos. Super admin only."""
    _require_admin(current_user)
    query = select(Club).order_by(Club.created_at.desc())
    if not include_inactive:
        query = query.where(Club.is_active == True)
    if q:
        like = f"%{q}%"
        query = query.where(
            (Club.name.ilike(like)) | (Club.slug.ilike(like)) | (Club.city.ilike(like))
        )
    rows = (await db.execute(query)).scalars().all()
    out = []
    for c in rows:
        member_count = (await db.execute(
            select(func.count()).select_from(ClubMember)
            .where(ClubMember.club_id == c.id, ClubMember.status == "active")
        )).scalar() or 0
        staff_count = (await db.execute(
            select(func.count()).select_from(ClubStaff)
            .where(ClubStaff.club_id == c.id, ClubStaff.is_active == True)
        )).scalar() or 0
        out.append({
            "id": str(c.id),
            "name": c.name,
            "slug": c.slug,
            "city": c.city,
            "state": c.country,  # state field doesn't exist in current schema, reuse country for now
            "country": c.country,
            "currency": c.currency,
            "phone": c.phone,
            "email": c.email,
            "plan_id": c.plan_id,
            "plan_expires_at": c.plan_expires_at.isoformat() if c.plan_expires_at else None,
            "is_active": c.is_active,
            "is_verified": c.is_verified,
            "member_count": member_count,
            "staff_count": staff_count,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return out


@router.get("/clubs/plans")
async def list_subscription_plans(current_user: CurrentUser, db: DB):
    """Lista de planes disponibles para asignar a clubes."""
    _require_admin(current_user)
    rows = (await db.execute(
        text("SELECT id, code, name, plan_type, price_monthly, price_yearly, max_members, features FROM subscription_plans WHERE plan_type='club' AND is_active=true ORDER BY price_monthly ASC")
    )).all()
    return [
        {
            "id": r[0], "code": r[1], "name": r[2], "plan_type": r[3],
            "price_monthly": float(r[4]) if r[4] is not None else 0,
            "price_yearly": float(r[5]) if r[5] is not None else 0,
            "max_members": r[6], "features": r[7],
        }
        for r in rows
    ]


@router.post("/clubs", status_code=201)
async def create_club_as_admin(data: ClubCreatePayload, current_user: CurrentUser, db: DB):
    """Crea un club SaaS con plan asignado. Opcionalmente designa al admin del club."""
    _require_admin(current_user)
    slug = _slugify(data.name)
    # Asegurar unicidad
    existing = (await db.execute(select(Club).where(Club.slug == slug))).scalar_one_or_none()
    if existing:
        slug = f"{slug}-{_uuid.uuid4().hex[:6]}"

    club = Club(
        name=data.name,
        slug=slug,
        city=data.city,
        country=data.country or "MX",
        phone=data.phone,
        email=data.email,
        currency=data.currency or "MXN",
        timezone=data.timezone or "America/Mexico_City",
        plan_id=data.plan_id,
        is_active=True,
        is_verified=True,  # creado por super admin → verificado
    )
    db.add(club)
    await db.flush()

    # Si se especificó admin_user_id, asignarlo como staff con rol owner
    if data.admin_user_id:
        try:
            admin_uuid = _uuid.UUID(data.admin_user_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="admin_user_id inválido")
        user_check = await db.execute(select(User).where(User.id == admin_uuid))
        if not user_check.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Usuario admin no encontrado")
        staff = ClubStaff(club_id=club.id, user_id=admin_uuid, role="owner", is_active=True)
        db.add(staff)

    return {
        "id": str(club.id),
        "slug": club.slug,
        "name": club.name,
        "plan_id": club.plan_id,
        "is_active": club.is_active,
    }


@router.patch("/clubs/{club_id}")
async def update_club(club_id: str, data: ClubPatchPayload, current_user: CurrentUser, db: DB):
    """Actualiza datos del club: plan, status, info de contacto. Super admin only."""
    _require_admin(current_user)
    result = await db.execute(select(Club).where(Club.id == _uuid.UUID(club_id)))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(club, field, value)
    await db.flush()
    return {"id": str(club.id), "slug": club.slug, "is_active": club.is_active, "plan_id": club.plan_id}


class AddStaffPayload(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    role: str = "admin"


@router.post("/clubs/{club_id}/staff")
async def add_club_staff(club_id: str, payload: AddStaffPayload, current_user: CurrentUser, db: DB):
    """Asigna un usuario como staff del club. Acepta user_id, email o username."""
    _require_admin(current_user)
    if payload.role not in ("owner", "admin", "manager", "staff"):
        raise HTTPException(status_code=422, detail="Rol inválido")
    club_uuid = _uuid.UUID(club_id)
    club_res = await db.execute(select(Club).where(Club.id == club_uuid))
    if not club_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Club no encontrado")

    user = None
    if payload.user_id:
        user_res = await db.execute(select(User).where(User.id == _uuid.UUID(payload.user_id)))
        user = user_res.scalar_one_or_none()
    elif payload.email:
        user_res = await db.execute(select(User).where(User.email == payload.email.lower().strip()))
        user = user_res.scalar_one_or_none()
    elif payload.username:
        user_res = await db.execute(select(User).where(User.username == payload.username.strip()))
        user = user_res.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado. Pídele que se registre primero en golfbookvip.com.")

    existing = await db.execute(
        select(ClubStaff).where(ClubStaff.club_id == club_uuid, ClubStaff.user_id == user.id)
    )
    staff = existing.scalar_one_or_none()
    if staff:
        staff.role = payload.role
        staff.is_active = True
    else:
        staff = ClubStaff(club_id=club_uuid, user_id=user.id, role=payload.role, is_active=True)
        db.add(staff)
    await db.flush()
    return {
        "club_id": club_id,
        "user_id": str(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "username": user.username,
        "role": payload.role,
    }


@router.delete("/clubs/{club_id}/staff/{user_id}")
async def remove_club_staff(club_id: str, user_id: str, current_user: CurrentUser, db: DB):
    """Quita acceso de staff a un usuario."""
    _require_admin(current_user)
    result = await db.execute(
        select(ClubStaff).where(
            ClubStaff.club_id == _uuid.UUID(club_id),
            ClubStaff.user_id == _uuid.UUID(user_id),
        )
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff no encontrado")
    staff.is_active = False
    await db.flush()
    return {"club_id": club_id, "user_id": user_id, "is_active": False}


# ─── Recordatorios de tee time (cron) — v1.20.0 ────────────────────────────


@router.post("/notifications/process-reminders")
async def process_tee_time_reminders(
    db: DB,
    x_reminder_token: Optional[str] = Header(default=None),
):
    """Endpoint cron-friendly: envía recordatorios 24h y 1h antes del tee time.

    Auth via header `X-Reminder-Token` con valor igual a `settings.REMINDER_CRON_TOKEN`.
    Si el token no está configurado en .env, el endpoint queda inaccesible (safe-by-default).

    Idempotente: solo envía si el flag correspondiente está en False; luego
    lo marca True. Se puede ejecutar cada N minutos sin duplicar mensajes.
    """
    if not settings.REMINDER_CRON_TOKEN or x_reminder_token != settings.REMINDER_CRON_TOKEN:
        raise HTTPException(status_code=403, detail="Token de cron inválido o no configurado")

    from app.models.tee_time import TeeTimeBooking, TeeTimeSlot, TeeTimeBookingPlayer
    from app.models.club import Club

    now = datetime.now(timezone.utc)
    sent_24h = 0
    sent_1h = 0

    # Funcion auxiliar para combinar slot.date + slot.time → datetime UTC aproximado
    # (asumimos timezone del club; aquí simplificamos y comparamos en UTC naive)
    async def _process_window(hours: int, lower: timedelta, upper: timedelta, flag_attr: str) -> int:
        """Busca bookings cuyo slot esté entre now+lower y now+upper, flag en False, y envía."""
        target_lower = (now + lower).replace(tzinfo=None)
        target_upper = (now + upper).replace(tzinfo=None)
        # Query: bookings confirmed con slot dentro de la ventana
        flag_col = getattr(TeeTimeBooking, flag_attr)
        q = (
            select(TeeTimeBooking, TeeTimeSlot, Club)
            .join(TeeTimeSlot, TeeTimeSlot.id == TeeTimeBooking.slot_id)
            .join(Club, Club.id == TeeTimeSlot.club_id)
            .where(
                TeeTimeBooking.status == "confirmed",
                flag_col == False,  # noqa: E712
                # Filtro grueso por date primero (rápido por índice)
                TeeTimeSlot.date >= target_lower.date(),
                TeeTimeSlot.date <= target_upper.date(),
            )
        )
        rows = (await db.execute(q)).all()
        count_sent = 0
        for booking, slot, club in rows:
            # Verificación fina del datetime combinado
            slot_dt = datetime.combine(slot.date, slot.time)
            if not (target_lower <= slot_dt <= target_upper):
                continue

            # Iterar players con user_id
            p_res = await db.execute(
                select(TeeTimeBookingPlayer).where(TeeTimeBookingPlayer.booking_id == booking.id)
            )
            user_ids = set()
            for p in p_res.scalars().all():
                if p.user_id:
                    user_ids.add(p.user_id)
            # Incluir al booker por si no está en los players
            user_ids.add(booking.user_id)

            panel_url = f"https://golfbookvip.com/es/club/{club.id}/tee-times"
            slot_date_str = slot.date.isoformat()
            slot_time_str = slot.time.strftime("%H:%M")
            for uid in user_ids:
                # Cargar user para nombre
                u_res = await db.execute(select(User).where(User.id == uid))
                u = u_res.scalar_one_or_none()
                if not u:
                    continue
                user_name = f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email
                subject, html = tpl_tee_time_reminder(
                    user_name, club.name, slot_date_str, slot_time_str, hours, panel_url,
                )
                tg_text = tg_tee_time_reminder(
                    user_name, club.name, slot_date_str, slot_time_str, hours, panel_url,
                )
                title = f"Recordatorio · Tee time en {hours}h" if hours >= 12 else f"Recordatorio · Tee time en 1h"
                body = f"{club.name} · {slot_date_str} {slot_time_str}"
                await notify_user(
                    db, uid, "tee_time_reminder", title, body,
                    data={"booking_id": str(booking.id), "club_id": str(club.id), "hours_until": hours},
                    email_subject=subject, email_html=html,
                    telegram_text=tg_text,
                    background_tasks=None,  # sync send dentro del cron
                )
            # Marcar flag
            setattr(booking, flag_attr, True)
            count_sent += 1
        return count_sent

    # Ventana 24h: slot entre now+22h y now+26h
    sent_24h = await _process_window(24, timedelta(hours=22), timedelta(hours=26), "reminder_24h_sent")
    # Ventana 1h: slot entre now+30min y now+1h30min
    sent_1h = await _process_window(1, timedelta(minutes=30), timedelta(hours=1, minutes=30), "reminder_1h_sent")

    await db.flush()
    return {"reminders_24h": sent_24h, "reminders_1h": sent_1h}

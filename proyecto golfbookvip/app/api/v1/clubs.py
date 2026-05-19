from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func, text, or_
from pydantic import BaseModel, Field
from typing import Optional
import uuid
import re
import secrets
from datetime import date, datetime, time as time_cls, timedelta, timezone

from app.core.deps import CurrentUser, DB
from app.models.club import Club, ClubStaff, ClubMember, MembershipType, MemberAccount, AccountTransaction
from app.models.tee_time import TeeTimeSlot, TeeTimeBooking, TeeTimeBookingPlayer
from app.models.user import User


# ─── Helpers de permisos por rol (Clubs SaaS Fase 1) ───────────────────────

ROLE_HIERARCHY = {"owner": 4, "admin": 3, "manager": 2, "staff": 1}


async def _get_club_role(db, club_id: uuid.UUID, user: User) -> Optional[str]:
    """Retorna el rol del user en el club, o None si no es staff."""
    if user.is_superadmin:
        return "owner"  # súper-admin tiene poder máximo
    res = await db.execute(
        select(ClubStaff).where(
            ClubStaff.club_id == club_id,
            ClubStaff.user_id == user.id,
            ClubStaff.is_active == True,
        )
    )
    s = res.scalar_one_or_none()
    return s.role if s else None


async def _require_club_role(db, club_id: uuid.UUID, user: User, min_role: str) -> str:
    """Verifica que el user tenga al menos `min_role` en el club. Devuelve el rol real."""
    role = await _get_club_role(db, club_id, user)
    if not role:
        raise HTTPException(status_code=403, detail="No tienes acceso a este club")
    if ROLE_HIERARCHY.get(role, 0) < ROLE_HIERARCHY.get(min_role, 99):
        raise HTTPException(status_code=403, detail=f"Requiere rol mínimo: {min_role}")
    return role

router = APIRouter()


def _generate_invite_code(club_name: str) -> str:
    """Genera código de invitación del estilo SLUG-XXXX. SLUG son los primeros 8 chars alfanum del nombre."""
    slug = re.sub(r"[^A-Z0-9]", "", (club_name or "").upper())[:8] or "CLUB"
    suffix = secrets.token_hex(2).upper()
    return f"{slug}-{suffix}"


# ─── Auto-onboarding por código de invitación (v1.16.0) ────────────────────


class JoinByCodePayload(BaseModel):
    invite_code: str


@router.get("/by-code/{invite_code}")
async def get_club_by_invite_code(invite_code: str, db: DB):
    """PÚBLICO: resuelve invite_code → info del club para la landing /join/{code}."""
    code = (invite_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=404, detail="Código no encontrado")
    res = await db.execute(select(Club).where(Club.invite_code == code, Club.is_active == True))
    club = res.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Código no encontrado")
    count_res = await db.execute(
        select(func.count()).select_from(ClubMember).where(
            ClubMember.club_id == club.id, ClubMember.status == "active"
        )
    )
    members_count = count_res.scalar_one() or 0
    return {
        "club_id": str(club.id),
        "name": club.name,
        "logo_url": club.logo_url,
        "city": club.city,
        "country": club.country,
        "members_count": members_count,
    }


@router.post("/by-code/join")
async def join_club_by_invite_code(payload: JoinByCodePayload, current_user: CurrentUser, db: DB):
    """AUTH: vincula al usuario actual como miembro del club asociado al invite_code.
    Idempotente: si ya es miembro retorna already_member=true sin error."""
    code = (payload.invite_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=404, detail="Código inválido")
    res = await db.execute(select(Club).where(Club.invite_code == code, Club.is_active == True))
    club = res.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Código no encontrado")
    existing = await db.execute(
        select(ClubMember).where(ClubMember.club_id == club.id, ClubMember.user_id == current_user.id)
    )
    member = existing.scalar_one_or_none()
    if member:
        if member.status != "active":
            member.status = "active"
            await db.flush()
        return {
            "club_id": str(club.id),
            "club_name": club.name,
            "member_id": str(member.id),
            "already_member": True,
        }
    member = ClubMember(
        club_id=club.id,
        user_id=current_user.id,
        membership_type_id=club.default_membership_type_id,
        joined_at=date.today(),
        status="active",
        onboarding_source="self_join",
    )
    db.add(member)
    await db.flush()
    return {
        "club_id": str(club.id),
        "club_name": club.name,
        "member_id": str(member.id),
        "already_member": False,
    }


class ClubCreate(BaseModel):
    name: str
    description: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    currency: str = "MXN"
    timezone: str = "America/Mexico_City"


def _club_out(club: Club, member_count: int = 0, is_member: bool = False, role: Optional[str] = None):
    return {
        "id": str(club.id),
        "name": club.name,
        "slug": club.slug,
        "description": club.description,
        "country": club.country,
        "city": club.city,
        "phone": club.phone,
        "email": club.email,
        "currency": club.currency,
        "member_count": member_count,
        "is_member": is_member,
        "role": role,
    }


@router.get("")
async def list_clubs(db: DB, search: Optional[str] = None):
    query = select(Club).where(Club.is_active == True).order_by(Club.name)
    if search:
        query = query.where(Club.name.ilike(f"%{search}%"))
    result = await db.execute(query)
    clubs = result.scalars().all()

    out = []
    for c in clubs:
        count_res = await db.execute(
            select(func.count()).where(ClubMember.club_id == c.id, ClubMember.status == "active")
        )
        out.append(_club_out(c, member_count=count_res.scalar() or 0))
    return out


@router.get("/mine")
async def my_clubs(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(ClubMember).where(ClubMember.user_id == current_user.id, ClubMember.status == "active")
    )
    memberships = result.scalars().all()
    out = []
    for m in memberships:
        c_res = await db.execute(select(Club).where(Club.id == m.club_id))
        club = c_res.scalar_one_or_none()
        if club:
            count_res = await db.execute(
                select(func.count()).where(ClubMember.club_id == club.id, ClubMember.status == "active")
            )
            # check if also staff/owner
            staff_res = await db.execute(
                select(ClubStaff).where(ClubStaff.club_id == club.id, ClubStaff.user_id == current_user.id)
            )
            staff = staff_res.scalar_one_or_none()
            out.append(_club_out(club, count_res.scalar() or 0, True, staff.role if staff else "member"))
    return out


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_club(data: ClubCreate, current_user: CurrentUser, db: DB):
    slug = re.sub(r"[^a-z0-9]+", "-", data.name.lower()).strip("-")
    existing = await db.execute(select(Club).where(Club.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{str(uuid.uuid4())[:8]}"

    # Generar invite_code único (con reintento en caso de colisión)
    invite_code = _generate_invite_code(data.name)
    for _ in range(5):
        check = await db.execute(select(Club).where(Club.invite_code == invite_code))
        if not check.scalar_one_or_none():
            break
        invite_code = _generate_invite_code(data.name)

    club = Club(slug=slug, invite_code=invite_code, **data.model_dump())
    db.add(club)
    await db.flush()

    staff = ClubStaff(club_id=club.id, user_id=current_user.id, role="owner")
    db.add(staff)

    member = ClubMember(
        club_id=club.id, user_id=current_user.id, status="active",
        joined_at=date.today(), onboarding_source="manual",
    )
    db.add(member)

    return {"id": str(club.id), "slug": club.slug, "name": club.name, "invite_code": club.invite_code}


@router.get("/{club_id}")
async def get_club(club_id: uuid.UUID, db: DB):
    result = await db.execute(select(Club).where(Club.id == club_id, Club.is_active == True))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado")
    count_res = await db.execute(
        select(func.count()).where(ClubMember.club_id == club_id, ClubMember.status == "active")
    )
    return _club_out(club, count_res.scalar() or 0)


@router.post("/{club_id}/join")
async def join_club(club_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Club).where(Club.id == club_id, Club.is_active == True))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Club no encontrado")

    existing = await db.execute(
        select(ClubMember).where(ClubMember.club_id == club_id, ClubMember.user_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ya eres miembro de este club")

    member = ClubMember(club_id=club_id, user_id=current_user.id, status="active", joined_at=date.today())
    db.add(member)
    return {"message": "Te has unido al club"}


@router.delete("/{club_id}/leave")
async def leave_club(club_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(ClubMember).where(ClubMember.club_id == club_id, ClubMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="No eres miembro de este club")
    member.status = "inactive"
    return {"message": "Has salido del club"}


@router.get("/{club_id}/members")
async def get_club_members(club_id: uuid.UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(ClubMember, User)
        .join(User, User.id == ClubMember.user_id)
        .where(ClubMember.club_id == club_id, ClubMember.status == "active")
        .order_by(User.first_name)
    )
    rows = result.all()
    return [
        {
            "user_id": str(m.user_id),
            "first_name": u.first_name,
            "last_name": u.last_name,
            "username": u.username,
            "handicap_index": float(u.handicap_index) if u.handicap_index else None,
            "member_number": m.member_number,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m, u in rows
    ]


# ─── Panel del cliente-admin (Clubs SaaS Fase 0.5) ─────────────────────────


@router.get("/staff/mine")
async def my_staff_clubs(current_user: CurrentUser, db: DB):
    """Lista los clubes donde el usuario actual es staff activo (owner, admin, manager, staff).

    Usado por el dashboard del jugador para detectar si tiene panel de cliente-admin.
    """
    result = await db.execute(
        select(ClubStaff, Club)
        .join(Club, Club.id == ClubStaff.club_id)
        .where(
            ClubStaff.user_id == current_user.id,
            ClubStaff.is_active == True,
            Club.is_active == True,
        )
        .order_by(Club.name)
    )
    rows = result.all()
    return [
        {
            "club_id": str(c.id),
            "club_name": c.name,
            "club_slug": c.slug,
            "club_city": c.city,
            "role": s.role,
            "joined_at": s.joined_at.isoformat() if s.joined_at else None,
        }
        for s, c in rows
    ]


@router.get("/{club_id}/dashboard")
async def club_dashboard(club_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Panel del cliente-admin: info del club + contadores + plan. Requiere ser staff o súper-admin."""
    # auth scoping
    if not current_user.is_superadmin:
        staff_res = await db.execute(
            select(ClubStaff).where(
                ClubStaff.club_id == club_id,
                ClubStaff.user_id == current_user.id,
                ClubStaff.is_active == True,
            )
        )
        if not staff_res.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="No tienes acceso a este club")

    c_res = await db.execute(select(Club).where(Club.id == club_id))
    club = c_res.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado")

    member_count_res = await db.execute(
        select(func.count()).where(ClubMember.club_id == club_id, ClubMember.status == "active")
    )
    staff_count_res = await db.execute(
        select(func.count()).where(ClubStaff.club_id == club_id, ClubStaff.is_active == True)
    )

    # plan (opcional)
    plan_info = None
    if club.plan_id:
        plan_row = await db.execute(
            text("SELECT id, code, name, plan_type, price_monthly, max_members FROM subscription_plans WHERE id = :pid").bindparams(pid=club.plan_id)
        )
        p = plan_row.first()
        if p:
            plan_info = {
                "id": p.id, "code": p.code, "name": p.name,
                "plan_type": p.plan_type,
                "price_monthly": float(p.price_monthly) if p.price_monthly else 0,
                "max_members": p.max_members,
            }

    return {
        "id": str(club.id),
        "name": club.name,
        "slug": club.slug,
        "description": club.description,
        "city": club.city,
        "country": club.country,
        "phone": club.phone,
        "email": club.email,
        "website": club.website,
        "currency": club.currency,
        "timezone": club.timezone,
        "logo_url": club.logo_url,
        "cover_url": club.cover_url,
        "is_active": club.is_active,
        "is_verified": club.is_verified,
        "access_type": club.access_type,
        "plan": plan_info,
        "plan_expires_at": club.plan_expires_at.isoformat() if club.plan_expires_at else None,
        "member_count": member_count_res.scalar() or 0,
        "staff_count": staff_count_res.scalar() or 0,
        "created_at": club.created_at.isoformat() if club.created_at else None,
    }


@router.get("/{club_id}/staff")
async def list_club_staff(club_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Lista el staff del club. Requiere ser staff del mismo club o súper-admin."""
    if not current_user.is_superadmin:
        own_res = await db.execute(
            select(ClubStaff).where(
                ClubStaff.club_id == club_id,
                ClubStaff.user_id == current_user.id,
                ClubStaff.is_active == True,
            )
        )
        if not own_res.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="No tienes acceso a este club")

    rows = await db.execute(
        select(ClubStaff, User)
        .join(User, User.id == ClubStaff.user_id)
        .where(ClubStaff.club_id == club_id, ClubStaff.is_active == True)
        .order_by(ClubStaff.role, User.first_name)
    )
    return [
        {
            "user_id": str(s.user_id),
            "first_name": u.first_name,
            "last_name": u.last_name,
            "username": u.username,
            "email": u.email,
            "role": s.role,
            "joined_at": s.joined_at.isoformat() if s.joined_at else None,
        }
        for s, u in rows.all()
    ]


@router.get("/{club_id}/my-role")
async def my_role_in_club(club_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Devuelve el rol del usuario actual en este club. Útil para que el frontend muestre/oculte botones."""
    role = await _get_club_role(db, club_id, current_user)
    return {
        "role": role,
        "is_superadmin": bool(current_user.is_superadmin),
        "can_manage_members": role in ("owner", "admin", "manager") if role else False,
        "can_manage_membership_types": role in ("owner", "admin") if role else False,
        "can_manage_staff": role == "owner" if role else False,
    }


# ─── Tipos de membresía (CRUD) ─────────────────────────────────────────────


class MembershipTypeIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    monthly_fee: float = 0
    yearly_fee: float = 0
    benefits: Optional[dict] = None


class MembershipTypePatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    monthly_fee: Optional[float] = None
    yearly_fee: Optional[float] = None
    benefits: Optional[dict] = None
    is_active: Optional[bool] = None


@router.get("/{club_id}/membership-types")
async def list_membership_types(club_id: uuid.UUID, current_user: CurrentUser, db: DB,
                                  include_inactive: bool = False):
    """Lista tipos de membresía del club. Requiere ser staff."""
    await _require_club_role(db, club_id, current_user, "staff")
    q = select(MembershipType).where(MembershipType.club_id == club_id)
    if not include_inactive:
        q = q.where(MembershipType.is_active == True)
    q = q.order_by(MembershipType.monthly_fee, MembershipType.name)
    res = await db.execute(q)
    types = res.scalars().all()
    # count members per type
    out = []
    for t in types:
        count_res = await db.execute(
            select(func.count()).where(
                ClubMember.membership_type_id == t.id,
                ClubMember.status == "active",
            )
        )
        out.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "monthly_fee": float(t.monthly_fee) if t.monthly_fee else 0,
            "yearly_fee": float(t.yearly_fee) if t.yearly_fee else 0,
            "benefits": t.benefits,
            "is_active": t.is_active,
            "member_count": count_res.scalar() or 0,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return out


@router.post("/{club_id}/membership-types", status_code=201)
async def create_membership_type(club_id: uuid.UUID, data: MembershipTypeIn, current_user: CurrentUser, db: DB):
    """Crear nuevo tipo de membresía. Requiere admin u owner."""
    await _require_club_role(db, club_id, current_user, "admin")
    mt = MembershipType(
        club_id=club_id,
        name=data.name,
        description=data.description,
        monthly_fee=data.monthly_fee,
        yearly_fee=data.yearly_fee,
        benefits=data.benefits,
        is_active=True,
    )
    db.add(mt)
    await db.flush()
    return {"id": mt.id, "name": mt.name}


@router.patch("/{club_id}/membership-types/{mt_id}")
async def update_membership_type(club_id: uuid.UUID, mt_id: int, data: MembershipTypePatch,
                                  current_user: CurrentUser, db: DB):
    """Editar tipo de membresía. Requiere admin u owner."""
    await _require_club_role(db, club_id, current_user, "admin")
    res = await db.execute(select(MembershipType).where(
        MembershipType.id == mt_id, MembershipType.club_id == club_id
    ))
    mt = res.scalar_one_or_none()
    if not mt:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(mt, k, v)
    await db.flush()
    return {"id": mt.id, "name": mt.name, "is_active": mt.is_active}


@router.delete("/{club_id}/membership-types/{mt_id}")
async def delete_membership_type(club_id: uuid.UUID, mt_id: int, current_user: CurrentUser, db: DB):
    """Soft-delete (is_active=False). Requiere admin u owner. No permitido si hay miembros activos asignados."""
    await _require_club_role(db, club_id, current_user, "admin")
    res = await db.execute(select(MembershipType).where(
        MembershipType.id == mt_id, MembershipType.club_id == club_id
    ))
    mt = res.scalar_one_or_none()
    if not mt:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    count_res = await db.execute(
        select(func.count()).where(
            ClubMember.membership_type_id == mt_id,
            ClubMember.status == "active",
        )
    )
    if (count_res.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: hay miembros activos con este tipo. Reasígnalos primero."
        )
    mt.is_active = False
    await db.flush()
    return {"id": mt.id, "is_active": False}


# ─── Miembros del club (Padrón) ─────────────────────────────────────────────


class MemberAddPayload(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    membership_type_id: Optional[int] = None
    member_number: Optional[str] = None
    joined_at: Optional[date] = None
    expires_at: Optional[date] = None
    notes: Optional[str] = None


class MemberPatchPayload(BaseModel):
    membership_type_id: Optional[int] = None
    member_number: Optional[str] = None
    status: Optional[str] = None
    expires_at: Optional[date] = None
    notes: Optional[str] = None


@router.get("/{club_id}/padron")
async def list_padron(club_id: uuid.UUID, current_user: CurrentUser, db: DB,
                       q: str = "", status_filter: str = "active",
                       membership_type_id: Optional[int] = None):
    """Lista padrón del club con filtros. Requiere ser staff."""
    await _require_club_role(db, club_id, current_user, "staff")
    query = (
        select(ClubMember, User, MembershipType)
        .join(User, User.id == ClubMember.user_id)
        .outerjoin(MembershipType, MembershipType.id == ClubMember.membership_type_id)
        .where(ClubMember.club_id == club_id)
    )
    if status_filter and status_filter != "all":
        query = query.where(ClubMember.status == status_filter)
    if membership_type_id:
        query = query.where(ClubMember.membership_type_id == membership_type_id)
    if q:
        like = f"%{q}%"
        query = query.where(or_(
            User.first_name.ilike(like),
            User.last_name.ilike(like),
            User.email.ilike(like),
            User.username.ilike(like),
            ClubMember.member_number.ilike(like),
        ))
    query = query.order_by(User.first_name, User.last_name)
    rows = (await db.execute(query)).all()
    return [
        {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "username": u.username,
            "handicap_index": float(u.handicap_index) if u.handicap_index is not None else None,
            "phone": getattr(u, "phone", None),
            "member_number": m.member_number,
            "status": m.status,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            "expires_at": m.expires_at.isoformat() if m.expires_at else None,
            "notes": m.notes,
            "membership_type": {
                "id": mt.id, "name": mt.name,
                "monthly_fee": float(mt.monthly_fee) if mt.monthly_fee else 0,
            } if mt else None,
        }
        for m, u, mt in rows
    ]


@router.post("/{club_id}/padron", status_code=201)
async def add_member_to_padron(club_id: uuid.UUID, payload: MemberAddPayload,
                                current_user: CurrentUser, db: DB):
    """Agrega un usuario al padrón. Requiere manager+ del club."""
    await _require_club_role(db, club_id, current_user, "manager")
    # buscar al user
    user = None
    if payload.user_id:
        u_res = await db.execute(select(User).where(User.id == uuid.UUID(payload.user_id)))
        user = u_res.scalar_one_or_none()
    elif payload.email:
        u_res = await db.execute(select(User).where(User.email == payload.email.lower().strip()))
        user = u_res.scalar_one_or_none()
    elif payload.username:
        u_res = await db.execute(select(User).where(User.username == payload.username.strip()))
        user = u_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado. Debe registrarse primero en golfbookvip.com.")
    # verificar que no esté ya
    existing = await db.execute(select(ClubMember).where(
        ClubMember.club_id == club_id, ClubMember.user_id == user.id
    ))
    member = existing.scalar_one_or_none()
    if member:
        if member.status == "active":
            raise HTTPException(status_code=409, detail="Este usuario ya es miembro activo")
        # reactivar si estaba inactivo
        member.status = "active"
        if payload.membership_type_id is not None:
            member.membership_type_id = payload.membership_type_id
        if payload.member_number:
            member.member_number = payload.member_number
        if payload.joined_at:
            member.joined_at = payload.joined_at
        if payload.expires_at:
            member.expires_at = payload.expires_at
        if payload.notes is not None:
            member.notes = payload.notes
    else:
        member = ClubMember(
            club_id=club_id,
            user_id=user.id,
            membership_type_id=payload.membership_type_id,
            member_number=payload.member_number,
            joined_at=payload.joined_at or date.today(),
            expires_at=payload.expires_at,
            notes=payload.notes,
            status="active",
        )
        db.add(member)
    await db.flush()
    return {
        "id": str(member.id),
        "user_id": str(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "member_number": member.member_number,
    }


# ─── Import masivo del padrón (v1.19.0) ────────────────────────────────────


class PadronImportRow(BaseModel):
    email: str
    member_number: Optional[str] = None
    membership_type_id: Optional[int] = None
    membership_type_name: Optional[str] = None
    joined_at: Optional[date] = None
    expires_at: Optional[date] = None
    notes: Optional[str] = None


class PadronImportPayload(BaseModel):
    rows: list[PadronImportRow] = Field(..., min_length=1, max_length=500)
    skip_existing: bool = True


@router.post("/{club_id}/padron/import", status_code=200)
async def import_padron(club_id: uuid.UUID, payload: PadronImportPayload,
                          current_user: CurrentUser, db: DB):
    """Importa filas del padrón en batch. Vincula a `users` existentes por email.
    Los emails no encontrados se reportan; no se crea cuenta automática (sin SMTP).
    Requiere manager+."""
    await _require_club_role(db, club_id, current_user, "manager")

    # Cargar club para obtener invite_code
    c_res = await db.execute(select(Club).where(Club.id == club_id))
    club = c_res.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado")

    # Cargar tipos de membresía del club (para resolver por nombre)
    types_res = await db.execute(select(MembershipType).where(
        MembershipType.club_id == club_id, MembershipType.is_active == True,
    ))
    types_by_id: dict[int, MembershipType] = {}
    types_by_name: dict[str, MembershipType] = {}
    for mt in types_res.scalars().all():
        types_by_id[mt.id] = mt
        types_by_name[mt.name.strip().lower()] = mt

    # Recolectar emails normalizados con sus índices originales
    emails_seen: set[str] = set()
    emails_to_lookup: list[str] = []
    rows_indexed: list[tuple[int, PadronImportRow, str]] = []  # (idx, row, normalized_email)
    duplicate_in_batch: list[dict] = []
    for i, row in enumerate(payload.rows):
        email_norm = (row.email or "").strip().lower()
        if not email_norm or "@" not in email_norm:
            duplicate_in_batch.append({"row_index": i, "email": row.email, "error": "email inválido"})
            continue
        if email_norm in emails_seen:
            duplicate_in_batch.append({"row_index": i, "email": email_norm, "error": "email duplicado en esta carga"})
            continue
        emails_seen.add(email_norm)
        emails_to_lookup.append(email_norm)
        rows_indexed.append((i, row, email_norm))

    # Buscar todos los users en un solo query
    users_by_email: dict[str, User] = {}
    if emails_to_lookup:
        u_res = await db.execute(select(User).where(User.email.in_(emails_to_lookup)))
        for u in u_res.scalars().all():
            users_by_email[u.email.lower()] = u

    # Buscar ClubMembers existentes para esos users
    existing_members: dict[uuid.UUID, ClubMember] = {}
    user_ids = [u.id for u in users_by_email.values()]
    if user_ids:
        em_res = await db.execute(select(ClubMember).where(
            ClubMember.club_id == club_id,
            ClubMember.user_id.in_(user_ids),
        ))
        for cm in em_res.scalars().all():
            existing_members[cm.user_id] = cm

    created: list[dict] = []
    reactivated: list[dict] = []
    skipped: list[dict] = []
    not_found: list[dict] = []
    errors: list[dict] = list(duplicate_in_batch)

    for idx, row, email_norm in rows_indexed:
        user = users_by_email.get(email_norm)
        if not user:
            not_found.append({"row_index": idx, "email": email_norm})
            continue

        # Resolver membership_type
        mt_id: Optional[int] = None
        if row.membership_type_id:
            if row.membership_type_id in types_by_id:
                mt_id = row.membership_type_id
            else:
                errors.append({"row_index": idx, "email": email_norm, "error": f"membership_type_id {row.membership_type_id} no pertenece al club"})
                continue
        elif row.membership_type_name:
            mt = types_by_name.get(row.membership_type_name.strip().lower())
            if mt:
                mt_id = mt.id
            # si no se encuentra, queda NULL silenciosamente — no es error fatal

        existing = existing_members.get(user.id)
        if existing:
            if existing.status == "active":
                if payload.skip_existing:
                    skipped.append({"row_index": idx, "email": email_norm, "user_id": str(user.id)})
                    continue
                else:
                    errors.append({"row_index": idx, "email": email_norm, "error": "ya es socio activo"})
                    continue
            # reactivar inactivo/suspendido
            existing.status = "active"
            if mt_id is not None:
                existing.membership_type_id = mt_id
            if row.member_number:
                existing.member_number = row.member_number
            if row.joined_at:
                existing.joined_at = row.joined_at
            if row.expires_at:
                existing.expires_at = row.expires_at
            if row.notes is not None:
                existing.notes = row.notes
            existing.onboarding_source = "manual_import"
            reactivated.append({"row_index": idx, "email": email_norm, "user_id": str(user.id)})
        else:
            new_member = ClubMember(
                club_id=club_id,
                user_id=user.id,
                membership_type_id=mt_id,
                member_number=row.member_number,
                joined_at=row.joined_at or date.today(),
                expires_at=row.expires_at,
                notes=row.notes,
                status="active",
                onboarding_source="manual_import",
            )
            db.add(new_member)
            created.append({"row_index": idx, "email": email_norm, "user_id": str(user.id)})

    await db.flush()

    # Construir link de invitación para compartir con los not_found
    invite_link = None
    if club.invite_code:
        invite_link = f"https://golfbookvip.com/es/join-club/{club.invite_code}"

    return {
        "total_rows": len(payload.rows),
        "created": len(created),
        "reactivated": len(reactivated),
        "skipped": len(skipped),
        "not_found_count": len(not_found),
        "error_count": len(errors),
        "details": {
            "created": created,
            "reactivated": reactivated,
            "skipped": skipped,
            "not_found": not_found,
            "errors": errors,
        },
        "invite_link": invite_link,
    }


@router.patch("/{club_id}/padron/{user_id}")
async def update_padron_member(club_id: uuid.UUID, user_id: uuid.UUID, payload: MemberPatchPayload,
                                current_user: CurrentUser, db: DB):
    """Edita un miembro del padrón. Requiere manager+ del club."""
    await _require_club_role(db, club_id, current_user, "manager")
    res = await db.execute(select(ClubMember).where(
        ClubMember.club_id == club_id, ClubMember.user_id == user_id
    ))
    member = res.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Miembro no encontrado")
    if payload.status and payload.status not in ("active", "inactive", "suspended"):
        raise HTTPException(status_code=422, detail="status inválido (active/inactive/suspended)")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(member, k, v)
    await db.flush()
    return {"id": str(member.id), "status": member.status}


@router.delete("/{club_id}/padron/{user_id}")
async def remove_from_padron(club_id: uuid.UUID, user_id: uuid.UUID,
                              current_user: CurrentUser, db: DB):
    """Marca miembro como inactivo (soft delete). Requiere manager+ del club."""
    await _require_club_role(db, club_id, current_user, "manager")
    res = await db.execute(select(ClubMember).where(
        ClubMember.club_id == club_id, ClubMember.user_id == user_id
    ))
    member = res.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Miembro no encontrado")
    member.status = "inactive"
    await db.flush()
    return {"id": str(member.id), "status": "inactive"}


# ─── Tee times (Clubs SaaS Fase 2) ─────────────────────────────────────────


class TeeTimeSlotIn(BaseModel):
    date: date
    time: str  # HH:MM
    max_players: int = 4
    tier: str = "members_only"
    green_fee_member: float = 0
    green_fee_guest: float = 0
    green_fee_public: float = 0


class TeeTimeSlotPatch(BaseModel):
    max_players: Optional[int] = None
    is_blocked: Optional[bool] = None
    block_reason: Optional[str] = None
    tier: Optional[str] = None
    green_fee_member: Optional[float] = None
    green_fee_guest: Optional[float] = None
    green_fee_public: Optional[float] = None


class TeeTimeGenerate(BaseModel):
    date_from: date
    date_to: date
    time_start: str = "06:00"
    time_end: str = "18:00"
    interval_minutes: int = Field(8, ge=2, le=60)
    max_players: int = Field(4, ge=1, le=8)
    weekdays: Optional[list[int]] = None  # 0=Mon, 6=Sun; None = todos
    tier: str = "members_only"
    green_fee_member: float = 0
    green_fee_guest: float = 0
    green_fee_public: float = 0


VALID_TIERS = {"members_only", "members_priority", "public"}


VALID_PLAYER_TYPES = {"member", "guest", "public"}


class BookingPlayerIn(BaseModel):
    player_type: str = Field(..., pattern="^(member|guest|public)$")
    user_id: Optional[uuid.UUID] = None      # member: requerido; guest/public: opcional si tiene cuenta
    guest_name: Optional[str] = None         # guest/public sin cuenta: requerido
    guest_email: Optional[str] = None
    sponsor_id: Optional[uuid.UUID] = None   # guest: requerido si club.guest_requires_sponsor


class BookingCreate(BaseModel):
    notes: Optional[str] = None
    user_id: Optional[uuid.UUID] = None      # admin: reservar por otro socio (= booker del booking)
    players: list[BookingPlayerIn] = Field(..., min_length=1, max_length=8)


def _calculate_fee(slot: TeeTimeSlot, player_type: str) -> float:
    if player_type == "member":
        return float(slot.green_fee_member or 0)
    if player_type == "guest":
        return float(slot.green_fee_guest or 0)
    if player_type == "public":
        return float(slot.green_fee_public or 0)
    return 0.0


async def _validate_booking(club: Club, slot: TeeTimeSlot, players: list[BookingPlayerIn],
                              booker_id: uuid.UUID, db) -> None:
    """Valida reglas duras del booking. Levanta HTTPException 422 con lista de errores. v1.17.0."""
    errors: list[str] = []
    today = date.today()

    # 1. max_players
    if len(players) > slot.max_players:
        errors.append(f"El slot permite máximo {slot.max_players} jugadores, recibidos {len(players)}")

    # 2. allow_guests
    has_guests_or_public = any(p.player_type in ("guest", "public") for p in players)
    if not club.allow_guests and has_guests_or_public:
        errors.append("Este club no permite invitados ni público; solo socios pueden reservar")

    # 3. guest_requires_sponsor
    guests = [p for p in players if p.player_type == "guest"]
    if club.guest_requires_sponsor and guests:
        for i, g in enumerate(guests):
            if not g.sponsor_id:
                errors.append(f"Invitado #{i+1} requiere sponsor (socio que lo invita)")

    # 4. max_guests_per_booking
    if len(guests) > club.max_guests_per_booking:
        errors.append(f"Máximo {club.max_guests_per_booking} invitados por reserva (recibidos {len(guests)})")

    # 5. Tier enforcement
    tier = slot.tier or "members_only"
    has_public = any(p.player_type == "public" for p in players)
    if tier == "members_only" and has_public:
        errors.append("Este slot es 'solo socios' — no admite jugadores públicos")
    if club.access_type == "private" and has_public:
        errors.append("Este club es privado — no admite jugadores públicos")

    # 6. Ventana de reserva para socios
    days_ahead = (slot.date - today).days
    if days_ahead > club.members_advance_days:
        errors.append(f"Los socios pueden reservar hasta {club.members_advance_days} días de anticipación (este slot está a {days_ahead} días)")
    # 6b. Ventana pública en members_priority
    if tier == "members_priority" and has_public and days_ahead > club.public_advance_days:
        errors.append(f"El público puede reservar a este slot prioritario solo dentro de {club.public_advance_days} días (faltan {days_ahead})")

    # 7. Validar members realmente sean socios activos del club
    for i, p in enumerate(players):
        if p.player_type == "member":
            if not p.user_id:
                errors.append(f"Jugador #{i+1} de tipo socio requiere user_id")
                continue
            m_res = await db.execute(select(ClubMember).where(
                ClubMember.club_id == club.id,
                ClubMember.user_id == p.user_id,
                ClubMember.status == "active",
            ))
            if not m_res.scalar_one_or_none():
                errors.append(f"Jugador #{i+1}: el usuario no es socio activo del club")
        elif p.player_type in ("guest", "public"):
            if not p.user_id and not (p.guest_name and p.guest_name.strip()):
                errors.append(f"Jugador #{i+1} de tipo {p.player_type} requiere user_id o nombre")

    # 8. Validar sponsors sean socios activos del club
    for i, g in enumerate(guests):
        if g.sponsor_id:
            s_res = await db.execute(select(ClubMember).where(
                ClubMember.club_id == club.id,
                ClubMember.user_id == g.sponsor_id,
                ClubMember.status == "active",
            ))
            if not s_res.scalar_one_or_none():
                errors.append(f"Invitado #{i+1}: el sponsor seleccionado no es socio activo del club")

    if errors:
        raise HTTPException(status_code=422, detail=errors)


def _parse_hhmm(s: str) -> time_cls:
    h, m = s.split(":")
    return time_cls(int(h), int(m))


@router.get("/{club_id}/tee-times")
async def list_tee_times(club_id: uuid.UUID, current_user: CurrentUser, db: DB,
                          date_from: Optional[date] = None, date_to: Optional[date] = None):
    """Lista slots del club con bookings. Requiere ser staff (cualquier rol) o miembro del club."""
    role = await _get_club_role(db, club_id, current_user)
    is_member = False
    if not role:
        # quizás es solo miembro del padrón (no staff), también puede ver el calendario
        m_res = await db.execute(select(ClubMember).where(
            ClubMember.club_id == club_id,
            ClubMember.user_id == current_user.id,
            ClubMember.status == "active",
        ))
        is_member = m_res.scalar_one_or_none() is not None
        if not (is_member or current_user.is_superadmin):
            raise HTTPException(status_code=403, detail="No tienes acceso a este club")

    if not date_from:
        date_from = date.today()
    if not date_to:
        date_to = date_from + timedelta(days=14)

    q = select(TeeTimeSlot).where(
        TeeTimeSlot.club_id == club_id,
        TeeTimeSlot.date >= date_from,
        TeeTimeSlot.date <= date_to,
    ).order_by(TeeTimeSlot.date, TeeTimeSlot.time)
    slots = (await db.execute(q)).scalars().all()

    out = []
    for s in slots:
        bookings_res = await db.execute(
            select(TeeTimeBooking, User)
            .join(User, User.id == TeeTimeBooking.user_id)
            .where(TeeTimeBooking.slot_id == s.id, TeeTimeBooking.status != "cancelled")
            .order_by(TeeTimeBooking.booked_at)
        )
        bookings = []
        for b, u in bookings_res.all():
            players_resolved = await _resolve_players_for_booking(db, b.id)
            bookings.append({
                "id": str(b.id),
                "user_id": str(b.user_id),
                "user_name": f"{u.first_name} {u.last_name}",
                "user_email": u.email,
                "players_count": b.players_count,
                "status": b.status,
                "notes": b.notes,
                "booked_at": b.booked_at.isoformat() if b.booked_at else None,
                "players": players_resolved,
                "total_fees": sum(p["fee_amount"] for p in players_resolved),
            })
        booked_total = sum(bk["players_count"] for bk in bookings if bk["status"] in ("pending", "confirmed"))
        out.append({
            "id": s.id,
            "date": s.date.isoformat(),
            "time": s.time.strftime("%H:%M"),
            "max_players": s.max_players,
            "available_spots": s.max_players - booked_total,
            "booked_count": booked_total,
            "is_blocked": s.is_blocked,
            "block_reason": s.block_reason,
            "tier": s.tier or "members_only",
            "green_fee_member": float(s.green_fee_member or 0),
            "green_fee_guest": float(s.green_fee_guest or 0),
            "green_fee_public": float(s.green_fee_public or 0),
            "bookings": bookings,
        })
    return out


@router.post("/{club_id}/tee-times/generate", status_code=201)
async def generate_tee_times(club_id: uuid.UUID, data: TeeTimeGenerate,
                              current_user: CurrentUser, db: DB):
    """Genera slots en bulk. Requiere admin+ del club."""
    await _require_club_role(db, club_id, current_user, "admin")
    if data.date_to < data.date_from:
        raise HTTPException(status_code=422, detail="date_to debe ser >= date_from")
    if (data.date_to - data.date_from).days > 90:
        raise HTTPException(status_code=422, detail="Rango máximo 90 días por generación")
    if data.tier not in VALID_TIERS:
        raise HTTPException(status_code=422, detail=f"tier inválido (válidos: {', '.join(VALID_TIERS)})")

    t_start = _parse_hhmm(data.time_start)
    t_end = _parse_hhmm(data.time_end)
    if t_end <= t_start:
        raise HTTPException(status_code=422, detail="time_end debe ser > time_start")

    created = 0
    skipped = 0
    cur = data.date_from
    while cur <= data.date_to:
        if data.weekdays is not None and cur.weekday() not in data.weekdays:
            cur += timedelta(days=1)
            continue
        # generar slots del día
        cur_dt = datetime.combine(cur, t_start)
        end_dt = datetime.combine(cur, t_end)
        while cur_dt < end_dt:
            cur_time = cur_dt.time()
            # verificar duplicado
            exists_res = await db.execute(select(TeeTimeSlot).where(
                TeeTimeSlot.club_id == club_id,
                TeeTimeSlot.date == cur,
                TeeTimeSlot.time == cur_time,
            ))
            if not exists_res.scalar_one_or_none():
                db.add(TeeTimeSlot(
                    club_id=club_id,
                    date=cur,
                    time=cur_time,
                    max_players=data.max_players,
                    available_spots=data.max_players,
                    tier=data.tier,
                    green_fee_member=data.green_fee_member,
                    green_fee_guest=data.green_fee_guest,
                    green_fee_public=data.green_fee_public,
                ))
                created += 1
            else:
                skipped += 1
            cur_dt += timedelta(minutes=data.interval_minutes)
        cur += timedelta(days=1)
    await db.flush()
    return {"created": created, "skipped": skipped}


@router.post("/{club_id}/tee-times", status_code=201)
async def create_tee_time_slot(club_id: uuid.UUID, data: TeeTimeSlotIn,
                                current_user: CurrentUser, db: DB):
    """Crear un slot individual. Requiere admin+ del club."""
    await _require_club_role(db, club_id, current_user, "admin")
    if data.tier not in VALID_TIERS:
        raise HTTPException(status_code=422, detail=f"tier inválido (válidos: {', '.join(VALID_TIERS)})")
    t = _parse_hhmm(data.time)
    exists = await db.execute(select(TeeTimeSlot).where(
        TeeTimeSlot.club_id == club_id, TeeTimeSlot.date == data.date, TeeTimeSlot.time == t
    ))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe un slot en esa fecha y hora")
    slot = TeeTimeSlot(
        club_id=club_id, date=data.date, time=t,
        max_players=data.max_players, available_spots=data.max_players,
        tier=data.tier,
        green_fee_member=data.green_fee_member,
        green_fee_guest=data.green_fee_guest,
        green_fee_public=data.green_fee_public,
    )
    db.add(slot)
    await db.flush()
    return {"id": slot.id, "date": slot.date.isoformat(), "time": slot.time.strftime("%H:%M")}


@router.patch("/{club_id}/tee-times/{slot_id}")
async def update_tee_time_slot(club_id: uuid.UUID, slot_id: int, data: TeeTimeSlotPatch,
                                current_user: CurrentUser, db: DB):
    """Editar/bloquear slot. Requiere admin+ del club."""
    await _require_club_role(db, club_id, current_user, "admin")
    res = await db.execute(select(TeeTimeSlot).where(
        TeeTimeSlot.id == slot_id, TeeTimeSlot.club_id == club_id
    ))
    slot = res.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot no encontrado")
    payload = data.model_dump(exclude_unset=True)
    if "tier" in payload and payload["tier"] not in VALID_TIERS:
        raise HTTPException(status_code=422, detail=f"tier inválido (válidos: {', '.join(VALID_TIERS)})")
    for k, v in payload.items():
        setattr(slot, k, v)
    await db.flush()
    return {"id": slot.id, "is_blocked": slot.is_blocked, "tier": slot.tier}


class TeeTimeSlotBulkPatch(BaseModel):
    date_from: date
    date_to: date
    time_start: Optional[str] = None  # HH:MM
    time_end: Optional[str] = None
    weekdays: Optional[list[int]] = None
    tier: Optional[str] = None
    green_fee_member: Optional[float] = None
    green_fee_guest: Optional[float] = None
    green_fee_public: Optional[float] = None


@router.patch("/{club_id}/tee-times/bulk")
async def bulk_update_tee_times(club_id: uuid.UUID, data: TeeTimeSlotBulkPatch,
                                  current_user: CurrentUser, db: DB):
    """Aplicar cambios a múltiples slots existentes (rango fechas/horas). Requiere admin+."""
    await _require_club_role(db, club_id, current_user, "admin")
    if data.tier and data.tier not in VALID_TIERS:
        raise HTTPException(status_code=422, detail=f"tier inválido (válidos: {', '.join(VALID_TIERS)})")
    q = select(TeeTimeSlot).where(
        TeeTimeSlot.club_id == club_id,
        TeeTimeSlot.date >= data.date_from,
        TeeTimeSlot.date <= data.date_to,
    )
    if data.time_start:
        q = q.where(TeeTimeSlot.time >= _parse_hhmm(data.time_start))
    if data.time_end:
        q = q.where(TeeTimeSlot.time < _parse_hhmm(data.time_end))
    slots = (await db.execute(q)).scalars().all()
    updated = 0
    for s in slots:
        if data.weekdays is not None and s.date.weekday() not in data.weekdays:
            continue
        if data.tier is not None: s.tier = data.tier
        if data.green_fee_member is not None: s.green_fee_member = data.green_fee_member
        if data.green_fee_guest is not None: s.green_fee_guest = data.green_fee_guest
        if data.green_fee_public is not None: s.green_fee_public = data.green_fee_public
        updated += 1
    await db.flush()
    return {"updated": updated}


@router.delete("/{club_id}/tee-times/{slot_id}")
async def delete_tee_time_slot(club_id: uuid.UUID, slot_id: int,
                                current_user: CurrentUser, db: DB):
    """Eliminar slot. Requiere admin+ del club. Solo si no tiene bookings activas."""
    await _require_club_role(db, club_id, current_user, "admin")
    res = await db.execute(select(TeeTimeSlot).where(
        TeeTimeSlot.id == slot_id, TeeTimeSlot.club_id == club_id
    ))
    slot = res.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot no encontrado")
    # verificar bookings activas
    bk_res = await db.execute(select(func.count()).where(
        TeeTimeBooking.slot_id == slot_id,
        TeeTimeBooking.status.in_(["pending", "confirmed"]),
    ))
    if (bk_res.scalar() or 0) > 0:
        raise HTTPException(status_code=409, detail="No se puede eliminar: el slot tiene reservas activas")
    await db.delete(slot)
    await db.flush()
    return {"id": slot_id, "deleted": True}


@router.post("/{club_id}/tee-times/{slot_id}/book", status_code=201)
async def book_tee_time(club_id: uuid.UUID, slot_id: int, data: BookingCreate,
                         current_user: CurrentUser, db: DB):
    """Reservar un slot con lista detallada de jugadores. v1.17.0.

    Cualquier socio del padrón puede reservar para sí. Staff puede reservar a nombre de otro (campo user_id).
    `players[]` lista todos los jugadores (incluido el booker). Tipos: member | guest | public.
    Valida: max_players, allow_guests, guest_requires_sponsor, max_guests_per_booking, tier (members_only / members_priority),
    members_advance_days, public_advance_days, access_type=private.
    Fees por jugador se calculan según tier del slot y se persisten (cobro real llega en v1.18).
    """
    # 1. Cargar slot
    s_res = await db.execute(select(TeeTimeSlot).where(
        TeeTimeSlot.id == slot_id, TeeTimeSlot.club_id == club_id
    ))
    slot = s_res.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot no encontrado")
    if slot.is_blocked:
        raise HTTPException(status_code=409, detail=f"Slot bloqueado: {slot.block_reason or 'sin razón'}")
    if slot.date < date.today():
        raise HTTPException(status_code=409, detail="No puedes reservar slots pasados")

    # 2. Cargar club (para reglas de acceso)
    c_res = await db.execute(select(Club).where(Club.id == club_id))
    club = c_res.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado")

    # 3. Determinar booker (quién es responsable de la reserva)
    booker_id = current_user.id
    if data.user_id and data.user_id != current_user.id:
        role = await _get_club_role(db, club_id, current_user)
        if not role:
            raise HTTPException(status_code=403, detail="No tienes permisos para reservar a nombre de otro")
        booker_id = data.user_id

    # 4. Booker debe ser socio activo o staff (o superadmin)
    member_res = await db.execute(select(ClubMember).where(
        ClubMember.club_id == club_id, ClubMember.user_id == booker_id, ClubMember.status == "active",
    ))
    staff_res = await db.execute(select(ClubStaff).where(
        ClubStaff.club_id == club_id, ClubStaff.user_id == booker_id, ClubStaff.is_active == True,
    ))
    if not member_res.scalar_one_or_none() and not staff_res.scalar_one_or_none() and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Solo socios del padrón o staff pueden reservar")

    # 5. Disponibilidad del slot
    bk_res = await db.execute(select(func.coalesce(func.sum(TeeTimeBooking.players_count), 0)).where(
        TeeTimeBooking.slot_id == slot_id,
        TeeTimeBooking.status.in_(["pending", "confirmed"]),
    ))
    booked = bk_res.scalar() or 0
    if booked + len(data.players) > slot.max_players:
        raise HTTPException(status_code=409, detail=f"No hay cupo. Disponibles: {slot.max_players - booked}")

    # 6. Validación de reglas duras del booking
    await _validate_booking(club, slot, data.players, booker_id, db)

    # 7. Crear booking
    booking = TeeTimeBooking(
        slot_id=slot_id,
        user_id=booker_id,
        players_count=len(data.players),
        status="confirmed",
        notes=data.notes,
        confirmed_at=datetime.now(timezone.utc),
    )
    db.add(booking)
    await db.flush()

    # 8. Crear filas de players con fee calculado
    players_out = []
    for p in data.players:
        fee = _calculate_fee(slot, p.player_type)
        player_row = TeeTimeBookingPlayer(
            booking_id=booking.id,
            player_type=p.player_type,
            user_id=p.user_id,
            guest_name=(p.guest_name.strip() if p.guest_name else None),
            guest_email=(p.guest_email.strip().lower() if p.guest_email else None),
            sponsor_id=p.sponsor_id,
            fee_amount=fee,
            added_by=current_user.id,
        )
        db.add(player_row)
        players_out.append(player_row)
    await db.flush()

    # 9. Auto-cobro de green fees (v1.18.0): postea AccountTransaction por cada player payable
    fees_result = await _post_booking_fees(db, booking, slot, club, current_user)

    # 10. Response (resolved con nombres + info de cobro)
    resolved = await _resolve_players_for_booking(db, booking.id)
    total_fees = sum(r["fee_amount"] for r in resolved)
    return {
        "id": str(booking.id),
        "status": "confirmed",
        "slot_id": slot_id,
        "players_count": len(data.players),
        "total_fees": total_fees,
        "total_charged": fees_result["total_charged"],
        "charges_count": fees_result["transactions_count"],
        "players": resolved,
    }


async def _resolve_players_for_booking(db, booking_id: uuid.UUID) -> list[dict]:
    """Lista jugadores de un booking con nombres resueltos (join users) y nombre del sponsor."""
    rows_res = await db.execute(
        select(TeeTimeBookingPlayer).where(TeeTimeBookingPlayer.booking_id == booking_id)
        .order_by(TeeTimeBookingPlayer.created_at)
    )
    players = rows_res.scalars().all()
    if not players:
        return []
    # Cargar users de player.user_id y de sponsor_id (en un solo query)
    user_ids = {p.user_id for p in players if p.user_id} | {p.sponsor_id for p in players if p.sponsor_id}
    users_map: dict[uuid.UUID, User] = {}
    if user_ids:
        users_res = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in users_res.scalars().all():
            users_map[u.id] = u
    out = []
    for p in players:
        if p.user_id and p.user_id in users_map:
            u = users_map[p.user_id]
            name = f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email
            email = u.email
        else:
            name = p.guest_name or "(sin nombre)"
            email = p.guest_email
        sponsor_name = None
        if p.sponsor_id and p.sponsor_id in users_map:
            su = users_map[p.sponsor_id]
            sponsor_name = f"{su.first_name or ''} {su.last_name or ''}".strip() or su.email
        out.append({
            "id": str(p.id),
            "player_type": p.player_type,
            "user_id": str(p.user_id) if p.user_id else None,
            "name": name,
            "email": email,
            "sponsor_id": str(p.sponsor_id) if p.sponsor_id else None,
            "sponsor_name": sponsor_name,
            "fee_amount": float(p.fee_amount or 0),
        })
    return out


# ─── Auto-cobro de green fees (v1.18.0) ────────────────────────────────────


async def _post_booking_fees(db, booking: TeeTimeBooking, slot: TeeTimeSlot,
                               club: Club, current_user: User) -> dict:
    """Postea AccountTransaction(type='green_fee') por cada jugador del booking.

    Reglas de pago:
    - member → cargo a su propia cuenta
    - guest → sponsor (si guest_fee_to_sponsor) o cuenta propia (si tiene user_id), else SKIP
    - public → cuenta propia (si tiene user_id), else SKIP

    1 transaction por player_row (reference_id=player.id, reference_type='tee_time_booking_player').
    Salda negativo permitido (enforce_credit_limit=False).
    """
    players_res = await db.execute(
        select(TeeTimeBookingPlayer).where(TeeTimeBookingPlayer.booking_id == booking.id)
    )
    players = players_res.scalars().all()

    # Cargar nombres para descripción rica
    user_ids = {p.user_id for p in players if p.user_id} | {p.sponsor_id for p in players if p.sponsor_id}
    users_map: dict[uuid.UUID, User] = {}
    if user_ids:
        users_res = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in users_res.scalars().all():
            users_map[u.id] = u

    def _name_of(p: TeeTimeBookingPlayer) -> str:
        if p.user_id and p.user_id in users_map:
            u = users_map[p.user_id]
            return f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email or "(sin nombre)"
        return p.guest_name or "(sin nombre)"

    total_charged = 0.0
    tx_count = 0
    by_payer: dict[str, float] = {}

    for p in players:
        fee = float(p.fee_amount or 0)
        if fee <= 0:
            continue

        payer_id: Optional[uuid.UUID] = None
        if p.player_type == "member":
            payer_id = p.user_id
        elif p.player_type == "guest":
            if club.guest_fee_to_sponsor and p.sponsor_id:
                payer_id = p.sponsor_id
            else:
                payer_id = p.user_id  # puede ser None
        elif p.player_type == "public":
            payer_id = p.user_id  # puede ser None

        if payer_id is None:
            continue  # cash: queda solo en player.fee_amount

        acc = await _get_or_create_account(db, club.id, payer_id)
        slot_label = f"{slot.date.isoformat()} {slot.time.strftime('%H:%M')}"
        player_name = _name_of(p)
        if payer_id != p.user_id and p.player_type == "guest":
            # sponsor paga por guest → distinguir en la descripción
            desc = f"Green fee — {slot_label} · Invitado: {player_name}"
        else:
            desc = f"Green fee — {slot_label} · {player_name} ({p.player_type})"

        await _apply_transaction(
            db, acc, "green_fee", fee, desc, current_user,
            reference_id=str(p.id),
            reference_type="tee_time_booking_player",
            enforce_credit_limit=False,
        )
        total_charged += fee
        tx_count += 1
        key = str(payer_id)
        by_payer[key] = by_payer.get(key, 0.0) + fee

    return {"total_charged": total_charged, "transactions_count": tx_count, "by_payer": by_payer}


async def _refund_booking_fees(db, booking: TeeTimeBooking, current_user: User) -> dict:
    """Emite refund automático por cada green_fee posteado del booking. Idempotente:
    si ya existe un refund para ese player_id, lo salta."""
    # Cargar player_ids del booking
    players_res = await db.execute(
        select(TeeTimeBookingPlayer.id).where(TeeTimeBookingPlayer.booking_id == booking.id)
    )
    player_ids = [pid for (pid,) in players_res.all()]
    if not player_ids:
        return {"refunded_total": 0.0, "refund_count": 0}

    # Cargar charges existentes (type='green_fee')
    charges_res = await db.execute(
        select(AccountTransaction).where(
            AccountTransaction.reference_type == "tee_time_booking_player",
            AccountTransaction.reference_id.in_(player_ids),
            AccountTransaction.type == "green_fee",
        )
    )
    charges = charges_res.scalars().all()
    if not charges:
        return {"refunded_total": 0.0, "refund_count": 0}

    # Cargar refunds existentes para evitar duplicar
    refunds_res = await db.execute(
        select(AccountTransaction.reference_id).where(
            AccountTransaction.reference_type == "tee_time_booking_player",
            AccountTransaction.reference_id.in_(player_ids),
            AccountTransaction.type == "refund",
        )
    )
    refunded_player_ids = {rid for (rid,) in refunds_res.all()}

    refunded_total = 0.0
    refund_count = 0
    for ch in charges:
        if ch.reference_id in refunded_player_ids:
            continue
        # Cargar la cuenta del cargo original
        acc_res = await db.execute(select(MemberAccount).where(MemberAccount.id == ch.account_id))
        acc = acc_res.scalar_one_or_none()
        if not acc:
            continue
        amount = float(ch.amount or 0)
        original_desc = ch.description or "green fee"
        desc = f"Refund por cancelación · {original_desc}"
        await _apply_transaction(
            db, acc, "refund", amount, desc, current_user,
            reference_id=str(ch.reference_id),
            reference_type="tee_time_booking_player",
        )
        refunded_total += amount
        refund_count += 1

    return {"refunded_total": refunded_total, "refund_count": refund_count}


@router.delete("/{club_id}/tee-times/bookings/{booking_id}")
async def cancel_booking(club_id: uuid.UUID, booking_id: uuid.UUID,
                          current_user: CurrentUser, db: DB):
    """Cancelar reserva. El dueño de la reserva o staff (manager+) pueden cancelar."""
    b_res = await db.execute(
        select(TeeTimeBooking, TeeTimeSlot)
        .join(TeeTimeSlot, TeeTimeSlot.id == TeeTimeBooking.slot_id)
        .where(TeeTimeBooking.id == booking_id, TeeTimeSlot.club_id == club_id)
    )
    row = b_res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    booking, slot = row

    # permisos: el dueño puede cancelar siempre; staff manager+ del club también; superadmin también
    if booking.user_id != current_user.id and not current_user.is_superadmin:
        role = await _get_club_role(db, club_id, current_user)
        if not role or ROLE_HIERARCHY.get(role, 0) < ROLE_HIERARCHY["manager"]:
            raise HTTPException(status_code=403, detail="No tienes permisos para cancelar esta reserva")

    # Auto-refund de green fees posteados (v1.18.0). Idempotente: skip si ya hay refunds.
    refund_result = await _refund_booking_fees(db, booking, current_user)

    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    await db.flush()
    return {
        "id": str(booking.id),
        "status": "cancelled",
        "refunded_total": refund_result["refunded_total"],
        "refund_count": refund_result["refund_count"],
    }


@router.get("/{club_id}/tee-times/bookings/{booking_id}")
async def get_booking_detail(club_id: uuid.UUID, booking_id: uuid.UUID,
                              current_user: CurrentUser, db: DB):
    """Detalle de un booking con la lista resuelta de jugadores. v1.17.0.
    Permisos: el booker, sus sponsors, staff del club o superadmin."""
    res = await db.execute(
        select(TeeTimeBooking, TeeTimeSlot)
        .join(TeeTimeSlot, TeeTimeSlot.id == TeeTimeBooking.slot_id)
        .where(TeeTimeBooking.id == booking_id, TeeTimeSlot.club_id == club_id)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    booking, slot = row
    # permisos: booker o staff del club o superadmin
    if booking.user_id != current_user.id and not current_user.is_superadmin:
        role = await _get_club_role(db, club_id, current_user)
        if not role:
            raise HTTPException(status_code=403, detail="No tienes permisos para ver esta reserva")
    players = await _resolve_players_for_booking(db, booking.id)
    return {
        "id": str(booking.id),
        "slot_id": booking.slot_id,
        "date": slot.date.isoformat(),
        "time": slot.time.strftime("%H:%M"),
        "user_id": str(booking.user_id),
        "players_count": booking.players_count,
        "status": booking.status,
        "notes": booking.notes,
        "booked_at": booking.booked_at.isoformat() if booking.booked_at else None,
        "tier": slot.tier or "members_only",
        "players": players,
        "total_fees": sum(p["fee_amount"] for p in players),
    }


@router.get("/{club_id}/tee-times/bookings/{booking_id}/transactions")
async def list_booking_transactions(club_id: uuid.UUID, booking_id: uuid.UUID,
                                      current_user: CurrentUser, db: DB):
    """Lista AccountTransaction asociadas a un booking (charges + refunds de green fees). v1.18.0.
    Permisos: booker o staff del club."""
    res = await db.execute(
        select(TeeTimeBooking, TeeTimeSlot)
        .join(TeeTimeSlot, TeeTimeSlot.id == TeeTimeBooking.slot_id)
        .where(TeeTimeBooking.id == booking_id, TeeTimeSlot.club_id == club_id)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    booking, _slot = row
    if booking.user_id != current_user.id and not current_user.is_superadmin:
        role = await _get_club_role(db, club_id, current_user)
        if not role:
            raise HTTPException(status_code=403, detail="No tienes permisos para ver esta reserva")

    players_res = await db.execute(
        select(TeeTimeBookingPlayer.id).where(TeeTimeBookingPlayer.booking_id == booking_id)
    )
    player_ids = [pid for (pid,) in players_res.all()]
    if not player_ids:
        return []

    tx_res = await db.execute(
        select(AccountTransaction).where(
            AccountTransaction.reference_type == "tee_time_booking_player",
            AccountTransaction.reference_id.in_(player_ids),
        ).order_by(AccountTransaction.created_at)
    )
    rows = tx_res.scalars().all()
    return [
        {
            "id": str(t.id),
            "account_id": str(t.account_id),
            "type": t.type,
            "amount": float(t.amount or 0),
            "balance_after": float(t.balance_after or 0),
            "description": t.description,
            "reference_id": str(t.reference_id) if t.reference_id else None,
            "reference_type": t.reference_type,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in rows
    ]


@router.get("/{club_id}/tee-times/my-bookings")
async def my_bookings(club_id: uuid.UUID, current_user: CurrentUser, db: DB,
                       upcoming_only: bool = True):
    """Mis reservas en este club."""
    q = (
        select(TeeTimeBooking, TeeTimeSlot)
        .join(TeeTimeSlot, TeeTimeSlot.id == TeeTimeBooking.slot_id)
        .where(
            TeeTimeBooking.user_id == current_user.id,
            TeeTimeSlot.club_id == club_id,
            TeeTimeBooking.status != "cancelled",
        )
    )
    if upcoming_only:
        q = q.where(TeeTimeSlot.date >= date.today())
    q = q.order_by(TeeTimeSlot.date, TeeTimeSlot.time)
    rows = (await db.execute(q)).all()
    return [
        {
            "id": str(b.id),
            "slot_id": s.id,
            "date": s.date.isoformat(),
            "time": s.time.strftime("%H:%M"),
            "players_count": b.players_count,
            "status": b.status,
            "notes": b.notes,
        }
        for b, s in rows
    ]


# ─── Estado de cuenta (Clubs SaaS Fase 3) ─────────────────────────────────

# Convención del balance:
#   balance > 0 => saldo a favor del socio (crédito)
#   balance < 0 => deuda del socio con el club
# Tipos que SUMAN al balance (saldo a favor): payment, credit, refund
# Tipos que RESTAN del balance (deuda):       charge, membership_fee, green_fee, bet_loss
# Tipo "other" usa el signo del amount tal cual

CHARGE_TYPES = {"charge", "membership_fee", "green_fee", "bet_loss"}
CREDIT_TYPES = {"payment", "credit", "refund", "bet_win"}


class ChargePayload(BaseModel):
    amount: float = Field(..., gt=0)
    type: str = "charge"
    description: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None


class PaymentPayload(BaseModel):
    amount: float = Field(..., gt=0)
    method: Optional[str] = None  # cash / card / transfer / etc.
    description: Optional[str] = None


class AdjustmentPayload(BaseModel):
    amount: float  # con signo
    description: str = Field(..., min_length=1)


async def _get_or_create_account(db, club_id: uuid.UUID, user_id: uuid.UUID) -> MemberAccount:
    res = await db.execute(select(MemberAccount).where(
        MemberAccount.club_id == club_id, MemberAccount.user_id == user_id
    ))
    acc = res.scalar_one_or_none()
    if acc:
        return acc
    acc = MemberAccount(club_id=club_id, user_id=user_id, balance=0, credit_limit=0, is_active=True)
    db.add(acc)
    await db.flush()
    return acc


@router.get("/{club_id}/accounts")
async def list_member_accounts(club_id: uuid.UUID, current_user: CurrentUser, db: DB,
                                only_debtors: bool = False, q: str = ""):
    """Lista resumen de cuentas del club. Requiere staff (cualquier rol)."""
    await _require_club_role(db, club_id, current_user, "staff")
    query = (
        select(MemberAccount, User)
        .join(User, User.id == MemberAccount.user_id)
        .where(MemberAccount.club_id == club_id, MemberAccount.is_active == True)
    )
    if only_debtors:
        query = query.where(MemberAccount.balance < 0)
    if q:
        like = f"%{q}%"
        query = query.where(or_(
            User.first_name.ilike(like),
            User.last_name.ilike(like),
            User.email.ilike(like),
        ))
    query = query.order_by(MemberAccount.balance, User.first_name)
    rows = (await db.execute(query)).all()
    return [
        {
            "account_id": str(a.id),
            "user_id": str(a.user_id),
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "balance": float(a.balance) if a.balance is not None else 0,
            "credit_limit": float(a.credit_limit) if a.credit_limit is not None else 0,
        }
        for a, u in rows
    ]


@router.get("/{club_id}/accounts/{user_id}")
async def get_member_account(club_id: uuid.UUID, user_id: uuid.UUID,
                              current_user: CurrentUser, db: DB):
    """Detalle de cuenta. El propio user, staff del club o súper-admin."""
    if current_user.id != user_id and not current_user.is_superadmin:
        await _require_club_role(db, club_id, current_user, "staff")

    acc = await _get_or_create_account(db, club_id, user_id)
    # info del user
    u_res = await db.execute(select(User).where(User.id == user_id))
    u = u_res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # info del miembro (status, member_number)
    m_res = await db.execute(select(ClubMember).where(
        ClubMember.club_id == club_id, ClubMember.user_id == user_id
    ))
    m = m_res.scalar_one_or_none()

    return {
        "account_id": str(acc.id),
        "user_id": str(u.id),
        "first_name": u.first_name,
        "last_name": u.last_name,
        "email": u.email,
        "username": u.username,
        "balance": float(acc.balance) if acc.balance is not None else 0,
        "credit_limit": float(acc.credit_limit) if acc.credit_limit is not None else 0,
        "is_active": acc.is_active,
        "member_number": m.member_number if m else None,
        "member_status": m.status if m else None,
        "created_at": acc.created_at.isoformat() if acc.created_at else None,
    }


@router.get("/{club_id}/accounts/{user_id}/transactions")
async def list_transactions(club_id: uuid.UUID, user_id: uuid.UUID,
                             current_user: CurrentUser, db: DB,
                             date_from: Optional[date] = None, date_to: Optional[date] = None,
                             type_filter: Optional[str] = None,
                             limit: int = 100):
    """Historial de transacciones. El propio user, staff o súper-admin."""
    if current_user.id != user_id and not current_user.is_superadmin:
        await _require_club_role(db, club_id, current_user, "staff")
    acc = await _get_or_create_account(db, club_id, user_id)

    q = select(AccountTransaction).where(AccountTransaction.account_id == acc.id)
    if date_from:
        q = q.where(AccountTransaction.created_at >= datetime.combine(date_from, time_cls.min, tzinfo=timezone.utc))
    if date_to:
        q = q.where(AccountTransaction.created_at <= datetime.combine(date_to, time_cls.max, tzinfo=timezone.utc))
    if type_filter:
        q = q.where(AccountTransaction.type == type_filter)
    q = q.order_by(AccountTransaction.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    # also fetch user names for created_by
    creator_ids = {r.created_by for r in rows if r.created_by}
    creator_names: dict[uuid.UUID, str] = {}
    if creator_ids:
        c_res = await db.execute(select(User).where(User.id.in_(creator_ids)))
        for c in c_res.scalars().all():
            creator_names[c.id] = f"{c.first_name} {c.last_name}"

    return [
        {
            "id": str(t.id),
            "type": t.type,
            "amount": float(t.amount),
            "balance_after": float(t.balance_after),
            "description": t.description,
            "reference_type": t.reference_type,
            "reference_id": str(t.reference_id) if t.reference_id else None,
            "created_by_name": creator_names.get(t.created_by) if t.created_by else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in rows
    ]


async def _apply_transaction(db, acc: MemberAccount, type_: str, amount: float,
                              description: str, current_user: User,
                              reference_id: Optional[str] = None,
                              reference_type: Optional[str] = None,
                              enforce_credit_limit: bool = True) -> AccountTransaction:
    """Aplica transacción y actualiza balance atomically. amount siempre positivo excepto 'other'.

    enforce_credit_limit=False permite saldo negativo más allá del credit_limit del socio
    (usado por auto-cobro de green fees de v1.18: el booking ya está confirmado y el cargo
    es derivado, no debe rechazarse aunque la cuenta no tenga línea de crédito).
    """
    # decidir signo aplicado al balance
    if type_ in CREDIT_TYPES:
        delta = abs(amount)
    elif type_ in CHARGE_TYPES:
        delta = -abs(amount)
    elif type_ == "other":
        delta = amount  # con signo
    else:
        raise HTTPException(status_code=422, detail=f"Tipo desconocido: {type_}")

    new_balance = float(acc.balance or 0) + delta

    # validar credit_limit si el balance va a quedar negativo
    if enforce_credit_limit and new_balance < 0:
        max_debt = -float(acc.credit_limit or 0)
        if new_balance < max_debt:
            raise HTTPException(
                status_code=409,
                detail=f"Excede el límite de crédito permitido. Balance quedaría en {new_balance:.2f}, límite: {max_debt:.2f}"
            )

    acc.balance = new_balance
    tx = AccountTransaction(
        account_id=acc.id,
        type=type_,
        amount=abs(amount) if type_ != "other" else amount,
        balance_after=new_balance,
        description=description,
        reference_id=uuid.UUID(reference_id) if reference_id else None,
        reference_type=reference_type,
        created_by=current_user.id,
    )
    db.add(tx)
    await db.flush()
    return tx


@router.post("/{club_id}/accounts/{user_id}/charge", status_code=201)
async def register_charge(club_id: uuid.UUID, user_id: uuid.UUID, payload: ChargePayload,
                           current_user: CurrentUser, db: DB):
    """Registrar cargo a la cuenta. Requiere manager+ del club."""
    await _require_club_role(db, club_id, current_user, "manager")
    if payload.type not in CHARGE_TYPES:
        raise HTTPException(status_code=422, detail=f"Tipo debe ser uno de: {', '.join(CHARGE_TYPES)}")
    acc = await _get_or_create_account(db, club_id, user_id)
    tx = await _apply_transaction(
        db, acc, payload.type, payload.amount,
        payload.description or payload.type,
        current_user, payload.reference_id, payload.reference_type,
    )
    return {
        "id": str(tx.id),
        "type": tx.type,
        "amount": float(tx.amount),
        "balance_after": float(tx.balance_after),
    }


@router.post("/{club_id}/accounts/{user_id}/payment", status_code=201)
async def register_payment(club_id: uuid.UUID, user_id: uuid.UUID, payload: PaymentPayload,
                            current_user: CurrentUser, db: DB):
    """Registrar pago del socio. Requiere manager+ del club."""
    await _require_club_role(db, club_id, current_user, "manager")
    acc = await _get_or_create_account(db, club_id, user_id)
    desc = payload.description or (f"Pago en {payload.method}" if payload.method else "Pago")
    tx = await _apply_transaction(db, acc, "payment", payload.amount, desc, current_user)
    return {
        "id": str(tx.id),
        "type": tx.type,
        "amount": float(tx.amount),
        "balance_after": float(tx.balance_after),
    }


@router.post("/{club_id}/accounts/{user_id}/adjust", status_code=201)
async def register_adjustment(club_id: uuid.UUID, user_id: uuid.UUID, payload: AdjustmentPayload,
                               current_user: CurrentUser, db: DB):
    """Ajuste manual con signo. Requiere admin+ del club (más sensible)."""
    await _require_club_role(db, club_id, current_user, "admin")
    if payload.amount == 0:
        raise HTTPException(status_code=422, detail="El monto del ajuste debe ser distinto de cero")
    acc = await _get_or_create_account(db, club_id, user_id)
    tx = await _apply_transaction(db, acc, "other", payload.amount, payload.description, current_user)
    return {
        "id": str(tx.id),
        "type": tx.type,
        "amount": float(tx.amount),
        "balance_after": float(tx.balance_after),
    }


@router.patch("/{club_id}/accounts/{user_id}/credit-limit")
async def set_credit_limit(club_id: uuid.UUID, user_id: uuid.UUID,
                            credit_limit: float, current_user: CurrentUser, db: DB):
    """Cambiar límite de crédito. Requiere admin+ del club."""
    await _require_club_role(db, club_id, current_user, "admin")
    if credit_limit < 0:
        raise HTTPException(status_code=422, detail="credit_limit debe ser >= 0")
    acc = await _get_or_create_account(db, club_id, user_id)
    acc.credit_limit = credit_limit
    await db.flush()
    return {"account_id": str(acc.id), "credit_limit": float(acc.credit_limit)}


@router.get("/{club_id}/my-account")
async def get_my_account(club_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Mi cuenta en este club (atajo para el socio)."""
    # verificar que sea miembro o staff
    role = await _get_club_role(db, club_id, current_user)
    if not role:
        m_res = await db.execute(select(ClubMember).where(
            ClubMember.club_id == club_id,
            ClubMember.user_id == current_user.id,
            ClubMember.status == "active",
        ))
        if not m_res.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="No eres miembro de este club")
    acc = await _get_or_create_account(db, club_id, current_user.id)
    return {
        "account_id": str(acc.id),
        "balance": float(acc.balance) if acc.balance is not None else 0,
        "credit_limit": float(acc.credit_limit) if acc.credit_limit is not None else 0,
    }


# ─── Configuración del club / Política de acceso (Fase 4) ──────────────────


class ClubSettingsPatch(BaseModel):
    access_type: Optional[str] = None  # private|semi_private|public
    allow_guests: Optional[bool] = None
    guest_requires_sponsor: Optional[bool] = None
    max_guests_per_booking: Optional[int] = Field(None, ge=0, le=10)
    max_guest_visits_per_year: Optional[int] = Field(None, ge=0, le=365)
    guest_fee_to_sponsor: Optional[bool] = None
    members_advance_days: Optional[int] = Field(None, ge=0, le=365)
    public_advance_days: Optional[int] = Field(None, ge=0, le=365)
    default_membership_type_id: Optional[int] = None


@router.get("/{club_id}/settings")
async def get_club_settings(club_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Lee la configuración del club (acceso + invitación). Requiere ser staff."""
    await _require_club_role(db, club_id, current_user, "staff")
    res = await db.execute(select(Club).where(Club.id == club_id))
    club = res.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado")
    return {
        "access_type": club.access_type,
        "allow_guests": club.allow_guests,
        "guest_requires_sponsor": club.guest_requires_sponsor,
        "max_guests_per_booking": club.max_guests_per_booking,
        "max_guest_visits_per_year": club.max_guest_visits_per_year,
        "guest_fee_to_sponsor": club.guest_fee_to_sponsor,
        "members_advance_days": club.members_advance_days,
        "public_advance_days": club.public_advance_days,
        "invite_code": club.invite_code,
        "default_membership_type_id": club.default_membership_type_id,
    }


@router.patch("/{club_id}/settings")
async def update_club_settings(club_id: uuid.UUID, payload: ClubSettingsPatch,
                                current_user: CurrentUser, db: DB):
    """Actualizar política de acceso del club. Requiere admin+."""
    await _require_club_role(db, club_id, current_user, "admin")
    if payload.access_type and payload.access_type not in ("private", "semi_private", "public"):
        raise HTTPException(status_code=422, detail="access_type inválido")
    res = await db.execute(select(Club).where(Club.id == club_id))
    club = res.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado")
    data = payload.model_dump(exclude_unset=True)
    # Validar que el default_membership_type_id pertenezca al club
    if "default_membership_type_id" in data and data["default_membership_type_id"] is not None:
        mt_check = await db.execute(select(MembershipType).where(
            MembershipType.id == data["default_membership_type_id"],
            MembershipType.club_id == club_id,
        ))
        if not mt_check.scalar_one_or_none():
            raise HTTPException(status_code=422, detail="default_membership_type_id no pertenece al club")
    for k, v in data.items():
        setattr(club, k, v)
    await db.flush()
    return {"ok": True, "access_type": club.access_type, "default_membership_type_id": club.default_membership_type_id}


# ─── Rotación de invite_code + búsqueda de usuarios (v1.16.0) ──────────────


@router.post("/{club_id}/invite-code/rotate")
async def rotate_invite_code(club_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Genera un nuevo invite_code para el club. Requiere admin+. El código viejo deja de funcionar."""
    await _require_club_role(db, club_id, current_user, "admin")
    res = await db.execute(select(Club).where(Club.id == club_id))
    club = res.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado")
    new_code = _generate_invite_code(club.name)
    for _ in range(5):
        check = await db.execute(select(Club).where(Club.invite_code == new_code, Club.id != club.id))
        if not check.scalar_one_or_none():
            break
        new_code = _generate_invite_code(club.name)
    club.invite_code = new_code
    await db.flush()
    return {"invite_code": club.invite_code}


@router.get("/{club_id}/users/search")
async def search_users_for_club(club_id: uuid.UUID, current_user: CurrentUser, db: DB,
                                  q: str = "", limit: int = 20):
    """Autocomplete sobre `users` para agregar al padrón. Excluye los que ya son miembros activos. Requiere manager+."""
    await _require_club_role(db, club_id, current_user, "manager")
    q = (q or "").strip()
    if len(q) < 3:
        return []
    like = f"%{q}%"
    # Subquery: user_ids que ya son miembros activos
    members_subq = select(ClubMember.user_id).where(
        ClubMember.club_id == club_id, ClubMember.status == "active"
    ).scalar_subquery()
    query = (
        select(User)
        .where(
            User.is_active == True,
            User.id.notin_(members_subq),
            or_(
                User.email.ilike(like),
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.username.ilike(like),
            ),
        )
        .order_by(User.first_name, User.last_name)
        .limit(min(max(limit, 1), 50))
    )
    rows = (await db.execute(query)).scalars().all()
    return [
        {
            "user_id": str(u.id),
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "username": u.username,
            "handicap_index": float(u.handicap_index) if u.handicap_index is not None else None,
        }
        for u in rows
    ]

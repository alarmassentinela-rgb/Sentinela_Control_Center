from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func, text, or_
from pydantic import BaseModel, Field
from typing import Optional
import uuid
import re
from datetime import date

from app.core.deps import CurrentUser, DB
from app.models.club import Club, ClubStaff, ClubMember, MembershipType
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

    club = Club(slug=slug, **data.model_dump())
    db.add(club)
    await db.flush()

    staff = ClubStaff(club_id=club.id, user_id=current_user.id, role="owner")
    db.add(staff)

    member = ClubMember(club_id=club.id, user_id=current_user.id, status="active", joined_at=date.today())
    db.add(member)

    return {"id": str(club.id), "slug": club.slug, "name": club.name}


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

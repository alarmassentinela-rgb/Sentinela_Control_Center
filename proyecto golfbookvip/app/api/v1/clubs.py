from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
import uuid
import re
from datetime import date

from app.core.deps import CurrentUser, DB
from app.models.club import Club, ClubStaff, ClubMember
from app.models.user import User

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

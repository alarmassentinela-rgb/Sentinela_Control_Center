import uuid
import secrets
import string
from typing import Optional

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.deps import CurrentUser, DB
from app.models.group import Group, GroupMember
from app.models.user import User

router = APIRouter()


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_private: bool = False
    max_members: Optional[int] = None


def _gen_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))


@router.get("")
async def list_my_groups(current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Group, GroupMember)
        .join(GroupMember, Group.id == GroupMember.group_id)
        .where(
            GroupMember.user_id == current_user.id,
            GroupMember.status == 'active',
            Group.is_active == True
        )
        .order_by(Group.created_at.desc())
    )
    rows = result.all()
    out = []
    for g, gm in rows:
        cnt = await db.scalar(
            select(func.count()).select_from(GroupMember)
            .where(GroupMember.group_id == g.id, GroupMember.status == 'active')
        )
        out.append({
            "id": str(g.id),
            "name": g.name,
            "description": g.description,
            "is_private": g.is_private,
            "max_members": g.max_members,
            "member_count": cnt or 0,
            "invite_code": g.invite_code if gm.role in ('owner', 'admin') else None,
            "my_role": gm.role,
        })
    return out


@router.post("", status_code=201)
async def create_group(data: GroupCreate, current_user: CurrentUser, db: DB):
    code = _gen_code()
    for _ in range(5):
        existing = await db.scalar(select(Group).where(Group.invite_code == code))
        if not existing:
            break
        code = _gen_code()

    group = Group(
        created_by=current_user.id,
        name=data.name,
        description=data.description,
        is_private=data.is_private,
        max_members=data.max_members,
        invite_code=code,
    )
    db.add(group)
    await db.flush()

    member = GroupMember(
        group_id=group.id,
        user_id=current_user.id,
        role='owner',
        status='active',
    )
    db.add(member)

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "is_private": group.is_private,
        "max_members": group.max_members,
        "member_count": 1,
        "invite_code": code,
        "my_role": "owner",
    }


@router.get("/join/{invite_code}")
async def get_group_by_invite(invite_code: str, current_user: CurrentUser, db: DB):
    """Preview group info before joining."""
    group = await db.scalar(
        select(Group).where(Group.invite_code == invite_code.upper(), Group.is_active == True)
    )
    if not group:
        raise HTTPException(404, "Código de invitación inválido")
    cnt = await db.scalar(
        select(func.count()).select_from(GroupMember)
        .where(GroupMember.group_id == group.id, GroupMember.status == 'active')
    )
    return {"id": str(group.id), "name": group.name, "description": group.description, "member_count": cnt or 0}


@router.post("/join/{invite_code}")
async def join_group(invite_code: str, current_user: CurrentUser, db: DB):
    group = await db.scalar(
        select(Group).where(Group.invite_code == invite_code.upper(), Group.is_active == True)
    )
    if not group:
        raise HTTPException(404, "Código de invitación inválido")

    existing = await db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group.id, GroupMember.user_id == current_user.id
        )
    )
    if existing:
        if existing.status == 'active':
            raise HTTPException(400, "Ya eres miembro de este grupo")
        existing.status = 'active'
        db.add(existing)
    else:
        cnt = await db.scalar(
            select(func.count()).select_from(GroupMember)
            .where(GroupMember.group_id == group.id, GroupMember.status == 'active')
        )
        if group.max_members and (cnt or 0) >= group.max_members:
            raise HTTPException(400, "El grupo está lleno")
        db.add(GroupMember(
            group_id=group.id, user_id=current_user.id,
            role='member', status='active',
        ))

    return {"group_id": str(group.id), "name": group.name}


@router.get("/{group_id}")
async def get_group(group_id: uuid.UUID, current_user: CurrentUser, db: DB):
    group = await db.scalar(
        select(Group).where(Group.id == group_id, Group.is_active == True)
    )
    if not group:
        raise HTTPException(404, "Grupo no encontrado")

    my_member = await db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id,
            GroupMember.status == 'active'
        )
    )
    if not my_member and group.is_private:
        raise HTTPException(403, "Grupo privado")

    result = await db.execute(
        select(GroupMember, User)
        .join(User, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id, GroupMember.status == 'active')
        .order_by(GroupMember.joined_at)
    )
    members = result.all()

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "is_private": group.is_private,
        "max_members": group.max_members,
        "member_count": len(members),
        "invite_code": group.invite_code if my_member and my_member.role in ('owner', 'admin') else None,
        "my_role": my_member.role if my_member else None,
        "created_by": str(group.created_by),
        "members": [
            {
                "user_id": str(gm.user_id),
                "username": u.username,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "handicap_index": float(u.handicap_index) if u.handicap_index else None,
                "role": gm.role,
                "joined_at": gm.joined_at.isoformat() if gm.joined_at else None,
            }
            for gm, u in members
        ],
    }


@router.delete("/{group_id}/members/{user_id}", status_code=204)
async def remove_member(group_id: uuid.UUID, user_id: uuid.UUID, current_user: CurrentUser, db: DB):
    my_member = await db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id,
            GroupMember.status == 'active'
        )
    )
    if not my_member or my_member.role not in ('owner', 'admin'):
        raise HTTPException(403, "Sin permisos")

    target = await db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.status == 'active'
        )
    )
    if not target:
        raise HTTPException(404, "Miembro no encontrado")
    if target.role == 'owner':
        raise HTTPException(400, "No puedes expulsar al creador")
    target.status = 'inactive'
    db.add(target)


@router.delete("/{group_id}/leave", status_code=204)
async def leave_group(group_id: uuid.UUID, current_user: CurrentUser, db: DB):
    member = await db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id,
            GroupMember.status == 'active'
        )
    )
    if not member:
        raise HTTPException(404, "No eres miembro de este grupo")
    if member.role == 'owner':
        raise HTTPException(400, "El creador no puede abandonar el grupo. Elimínalo en su lugar.")
    member.status = 'inactive'
    db.add(member)


@router.delete("/{group_id}", status_code=204)
async def delete_group(group_id: uuid.UUID, current_user: CurrentUser, db: DB):
    group = await db.scalar(
        select(Group).where(Group.id == group_id, Group.is_active == True)
    )
    if not group:
        raise HTTPException(404, "Grupo no encontrado")
    if group.created_by != current_user.id:
        raise HTTPException(403, "Solo el creador puede eliminar el grupo")
    group.is_active = False
    db.add(group)

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
from app.models.round import Round, RoundPlayer
from app.models.course import Course
from app.models.score import Score
from app.models.social import Post, PostComment, Reaction

router = APIRouter()


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_private: bool = False
    max_members: Optional[int] = None


class PostCreate(BaseModel):
    content: str


class CommentCreate(BaseModel):
    content: str


async def _group_and_membership(group_id: uuid.UUID, current_user, db):
    """Devuelve (group, my_member). 404 si no existe; 403 si privado y no miembro."""
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
    return group, my_member


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


@router.get("/{group_id}/rounds")
async def list_group_rounds(group_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Rondas asociadas a un grupo. Requiere membresía si el grupo es privado."""
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
        select(Round, Course)
        .outerjoin(Course, Course.id == Round.course_id)
        .where(Round.group_id == group_id)
        .order_by(Round.scheduled_at.desc())
        .limit(50)
    )
    rows = result.all()
    out = []
    for r, course in rows:
        pc = await db.scalar(
            select(func.count()).select_from(RoundPlayer).where(RoundPlayer.round_id == r.id)
        )
        out.append({
            "id": str(r.id),
            "name": r.name,
            "course_name": course.name if course else None,
            "game_format": r.game_format,
            "status": r.status,
            "holes_to_play": r.holes_to_play,
            "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
            "player_count": pc or 0,
        })
    return out


@router.get("/{group_id}/leaderboard")
async def group_leaderboard(group_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Tabla de posiciones del grupo sobre sus rondas FINALIZADAS.

    Por cada ronda finalizada del grupo se calcula el net total de cada jugador
    (net por hoyo, con fallback a gross si no hay net) y se determina el ganador
    (menor net) entre quienes completaron la ronda. Devuelve a los miembros con:
    rondas jugadas, victorias y mejor net, ordenados por victorias → handicap → mejor net.
    """
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

    # Miembros activos
    mres = await db.execute(
        select(GroupMember, User)
        .join(User, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id, GroupMember.status == 'active')
    )
    members = mres.all()
    stats = {
        str(u.id): {
            "user_id": str(u.id),
            "username": u.username,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "handicap_index": float(u.handicap_index) if u.handicap_index is not None else None,
            "rounds_played": 0,
            "wins": 0,
            "best_net": None,
        }
        for _, u in members
    }

    # Rondas finalizadas del grupo
    rres = await db.execute(
        select(Round).where(Round.group_id == group_id, Round.status == "finished")
    )
    rounds = rres.scalars().all()
    finished_count = len(rounds)

    for rd in rounds:
        holes_target = rd.holes_to_play or 18
        sres = await db.execute(select(Score).where(Score.round_id == rd.id))
        scores = sres.scalars().all()
        # Agregar net/holes por jugador
        agg: dict = {}
        for s in scores:
            uid = str(s.user_id)
            d = agg.setdefault(uid, {"net": 0, "holes": 0})
            if s.gross_score is not None:
                d["net"] += s.net_score if s.net_score is not None else s.gross_score
                d["holes"] += 1
        # Solo cuentan jugadores del grupo que completaron la ronda
        completed = {
            uid: d for uid, d in agg.items()
            if uid in stats and d["holes"] >= holes_target
        }
        for uid, d in completed.items():
            stats[uid]["rounds_played"] += 1
            bn = stats[uid]["best_net"]
            if bn is None or d["net"] < bn:
                stats[uid]["best_net"] = d["net"]
        if completed:
            best = min(d["net"] for d in completed.values())
            for uid, d in completed.items():
                if d["net"] == best:
                    stats[uid]["wins"] += 1

    def sort_key(s):
        hcp = s["handicap_index"]
        return (
            -s["wins"],
            hcp if hcp is not None else 999,
            s["best_net"] if s["best_net"] is not None else 10**9,
        )

    rows = sorted(stats.values(), key=sort_key)
    for i, r in enumerate(rows):
        r["position"] = i + 1
    return {"finished_rounds": finished_count, "leaderboard": rows}


# ─── Muro de posts del grupo ──────────────────────────────────────────────────

@router.get("/{group_id}/posts")
async def list_group_posts(group_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Muro del grupo: posts más recientes (anclados primero). Privado requiere membresía."""
    group, my_member = await _group_and_membership(group_id, current_user, db)

    result = await db.execute(
        select(Post, User)
        .join(User, User.id == Post.author_id)
        .where(Post.group_id == group_id, Post.is_deleted == False)
        .order_by(Post.is_pinned.desc(), Post.created_at.desc())
        .limit(100)
    )
    rows = result.all()
    post_ids = [p.id for p, _ in rows]

    # Likes del usuario actual sobre estos posts (una sola query)
    my_likes: set = set()
    if post_ids:
        lres = await db.execute(
            select(Reaction.target_id).where(
                Reaction.user_id == current_user.id,
                Reaction.target_type == "post",
                Reaction.target_id.in_(post_ids),
            )
        )
        my_likes = {tid for (tid,) in lres.all()}

    can_moderate = my_member is not None and my_member.role in ("owner", "admin")
    return [
        {
            "id": str(p.id),
            "content": p.content,
            "author": {
                "user_id": str(u.id),
                "username": u.username,
                "first_name": u.first_name,
                "last_name": u.last_name,
            },
            "is_pinned": p.is_pinned,
            "reactions_count": p.reactions_count or 0,
            "comments_count": p.comments_count or 0,
            "liked_by_me": p.id in my_likes,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "can_delete": str(u.id) == str(current_user.id) or can_moderate,
        }
        for p, u in rows
    ]


@router.post("/{group_id}/posts", status_code=201)
async def create_group_post(group_id: uuid.UUID, data: PostCreate, current_user: CurrentUser, db: DB):
    """Publica en el muro. Solo miembros activos (también en grupos públicos)."""
    _group, my_member = await _group_and_membership(group_id, current_user, db)
    if not my_member:
        raise HTTPException(403, "Debes ser miembro del grupo para publicar")
    content = (data.content or "").strip()
    if not content:
        raise HTTPException(400, "El mensaje no puede estar vacío")
    if len(content) > 2000:
        raise HTTPException(400, "El mensaje es demasiado largo (máx. 2000)")

    post = Post(
        author_id=current_user.id,
        group_id=group_id,
        content=content,
        post_type="regular",
        visibility="group",
    )
    db.add(post)
    await db.flush()
    return {
        "id": str(post.id),
        "content": post.content,
        "author": {
            "user_id": str(current_user.id),
            "username": current_user.username,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
        },
        "is_pinned": False,
        "reactions_count": 0,
        "comments_count": 0,
        "liked_by_me": False,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "can_delete": True,
    }


async def _get_group_post(group_id: uuid.UUID, post_id: uuid.UUID, db):
    post = await db.scalar(
        select(Post).where(
            Post.id == post_id, Post.group_id == group_id, Post.is_deleted == False
        )
    )
    if not post:
        raise HTTPException(404, "Publicación no encontrada")
    return post


@router.delete("/{group_id}/posts/{post_id}", status_code=204)
async def delete_group_post(group_id: uuid.UUID, post_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Borra (soft) un post: el autor, o un owner/admin del grupo."""
    _group, my_member = await _group_and_membership(group_id, current_user, db)
    post = await _get_group_post(group_id, post_id, db)
    is_author = str(post.author_id) == str(current_user.id)
    can_moderate = my_member is not None and my_member.role in ("owner", "admin")
    if not (is_author or can_moderate):
        raise HTTPException(403, "Sin permisos para borrar esta publicación")
    post.is_deleted = True
    db.add(post)


@router.post("/{group_id}/posts/{post_id}/react")
async def toggle_post_reaction(group_id: uuid.UUID, post_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Alterna el 'like' del usuario en un post."""
    _group, my_member = await _group_and_membership(group_id, current_user, db)
    if not my_member:
        raise HTTPException(403, "Debes ser miembro del grupo")
    post = await _get_group_post(group_id, post_id, db)

    existing = await db.scalar(
        select(Reaction).where(
            Reaction.user_id == current_user.id,
            Reaction.target_type == "post",
            Reaction.target_id == post_id,
        )
    )
    if existing:
        await db.delete(existing)
        post.reactions_count = max(0, (post.reactions_count or 0) - 1)
        liked = False
    else:
        db.add(Reaction(
            user_id=current_user.id, target_type="post",
            target_id=post_id, reaction_type="like",
        ))
        post.reactions_count = (post.reactions_count or 0) + 1
        liked = True
    db.add(post)
    return {"liked": liked, "reactions_count": post.reactions_count}


@router.get("/{group_id}/posts/{post_id}/comments")
async def list_post_comments(group_id: uuid.UUID, post_id: uuid.UUID, current_user: CurrentUser, db: DB):
    await _group_and_membership(group_id, current_user, db)
    await _get_group_post(group_id, post_id, db)
    result = await db.execute(
        select(PostComment, User)
        .join(User, User.id == PostComment.author_id)
        .where(PostComment.post_id == post_id, PostComment.is_deleted == False)
        .order_by(PostComment.created_at)
    )
    rows = result.all()
    return [
        {
            "id": str(c.id),
            "content": c.content,
            "author": {
                "user_id": str(u.id),
                "username": u.username,
                "first_name": u.first_name,
                "last_name": u.last_name,
            },
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "can_delete": str(u.id) == str(current_user.id),
        }
        for c, u in rows
    ]


@router.post("/{group_id}/posts/{post_id}/comments", status_code=201)
async def add_post_comment(group_id: uuid.UUID, post_id: uuid.UUID, data: CommentCreate, current_user: CurrentUser, db: DB):
    _group, my_member = await _group_and_membership(group_id, current_user, db)
    if not my_member:
        raise HTTPException(403, "Debes ser miembro del grupo para comentar")
    post = await _get_group_post(group_id, post_id, db)
    content = (data.content or "").strip()
    if not content:
        raise HTTPException(400, "El comentario no puede estar vacío")
    if len(content) > 1000:
        raise HTTPException(400, "El comentario es demasiado largo (máx. 1000)")

    comment = PostComment(post_id=post_id, author_id=current_user.id, content=content)
    db.add(comment)
    post.comments_count = (post.comments_count or 0) + 1
    db.add(post)
    await db.flush()
    return {
        "id": str(comment.id),
        "content": comment.content,
        "author": {
            "user_id": str(current_user.id),
            "username": current_user.username,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
        },
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "can_delete": True,
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

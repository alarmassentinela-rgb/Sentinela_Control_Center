from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select

from app.models.club import Club, ClubMember
from app.models.course import Course
from app.models.group import Group
from app.models.round import RoundPlayer
from app.models.subscription import SubscriptionPlan
from app.models.user import User


FREE_PLAYER_CODE = "free_player"
FREE_CLUB_CODE = "free_club"

CLUB_UPGRADES = {
    "free_club": "club_starter",
    "club_starter": "club_pro",
    "club_pro": "club_enterprise",
}
PLAYER_UPGRADES = {
    "free_player": "player_pro",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(expires_at: Optional[datetime]) -> bool:
    if not expires_at:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < _now()


async def _plan_by_code(db, code: str) -> SubscriptionPlan:
    plan = await db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.code == code,
            SubscriptionPlan.is_active == True,
        )
    )
    if not plan:
        raise HTTPException(status_code=500, detail=f"Plan base no encontrado: {code}")
    return plan


async def get_user_plan(db, user: User) -> SubscriptionPlan:
    if user.plan_id and not _is_expired(user.plan_expires_at):
        plan = await db.scalar(
            select(SubscriptionPlan).where(
                SubscriptionPlan.id == user.plan_id,
                SubscriptionPlan.is_active == True,
            )
        )
        if plan:
            return plan
    return await _plan_by_code(db, FREE_PLAYER_CODE)


async def get_club_plan(db, club: Club) -> SubscriptionPlan:
    if club.plan_id and not _is_expired(club.plan_expires_at):
        plan = await db.scalar(
            select(SubscriptionPlan).where(
                SubscriptionPlan.id == club.plan_id,
                SubscriptionPlan.is_active == True,
            )
        )
        if plan:
            return plan
    return await _plan_by_code(db, FREE_CLUB_CODE)


def plan_limit_error(code: str, current: int, limit: int, upgrade_hint: Optional[str]) -> None:
    raise HTTPException(
        status_code=402,
        detail={
            "code": "plan_limit",
            "resource": code,
            "current": current,
            "limit": limit,
            "message": f"Límite del plan alcanzado para {code}: {current}/{limit}",
            "upgrade_to": upgrade_hint,
        },
    )


async def enforce_club_member_limit(db, club: Club) -> None:
    plan = await get_club_plan(db, club)
    if plan.max_members is None:
        return
    current = await db.scalar(
        select(func.count()).select_from(ClubMember).where(
            ClubMember.club_id == club.id,
            ClubMember.status == "active",
        )
    ) or 0
    if current >= plan.max_members:
        plan_limit_error("club_members", current, plan.max_members, CLUB_UPGRADES.get(plan.code))


async def enforce_club_course_limit(db, club_id) -> None:
    club = await db.scalar(select(Club).where(Club.id == club_id, Club.is_active == True))
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado")
    plan = await get_club_plan(db, club)
    if plan.max_courses is None:
        return
    current = await db.scalar(
        select(func.count()).select_from(Course).where(
            Course.club_id == club_id,
            Course.is_active == True,
        )
    ) or 0
    if current >= plan.max_courses:
        plan_limit_error("club_courses", current, plan.max_courses, CLUB_UPGRADES.get(plan.code))


async def enforce_user_group_limit(db, user: User) -> None:
    plan = await get_user_plan(db, user)
    if plan.max_groups is None:
        return
    current = await db.scalar(
        select(func.count()).select_from(Group).where(
            Group.created_by == user.id,
            Group.is_active == True,
        )
    ) or 0
    if current >= plan.max_groups:
        plan_limit_error("user_groups", current, plan.max_groups, PLAYER_UPGRADES.get(plan.code))


def _money(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def _plan_payload(plan: SubscriptionPlan) -> dict:
    return {
        "id": plan.id,
        "code": plan.code,
        "name": plan.name,
        "plan_type": plan.plan_type,
        "price_monthly": _money(plan.price_monthly),
        "price_yearly": _money(plan.price_yearly),
        "limits": {
            "max_members": plan.max_members,
            "max_courses": plan.max_courses,
            "max_groups": plan.max_groups,
            "max_rounds_history": plan.max_rounds_history,
        },
    }


async def usage_for_user(db, user: User) -> dict:
    plan = await get_user_plan(db, user)
    groups_used = await db.scalar(
        select(func.count()).select_from(Group).where(
            Group.created_by == user.id,
            Group.is_active == True,
        )
    ) or 0
    rounds_used = await db.scalar(
        select(func.count()).select_from(RoundPlayer).where(RoundPlayer.user_id == user.id)
    ) or 0
    return {
        "plan": _plan_payload(plan),
        "usage": {
            "groups": {
                "current": groups_used,
                "limit": plan.max_groups,
                "upgrade_to": PLAYER_UPGRADES.get(plan.code),
            },
            "rounds_history": {
                "current": rounds_used,
                "limit": plan.max_rounds_history,
                "upgrade_to": PLAYER_UPGRADES.get(plan.code),
            },
        },
    }


async def usage_for_club(db, club: Club) -> dict:
    plan = await get_club_plan(db, club)
    members_used = await db.scalar(
        select(func.count()).select_from(ClubMember).where(
            ClubMember.club_id == club.id,
            ClubMember.status == "active",
        )
    ) or 0
    courses_used = await db.scalar(
        select(func.count()).select_from(Course).where(
            Course.club_id == club.id,
            Course.is_active == True,
        )
    ) or 0
    return {
        "plan": _plan_payload(plan),
        "usage": {
            "members": {
                "current": members_used,
                "limit": plan.max_members,
                "upgrade_to": CLUB_UPGRADES.get(plan.code),
            },
            "courses": {
                "current": courses_used,
                "limit": plan.max_courses,
                "upgrade_to": CLUB_UPGRADES.get(plan.code),
            },
        },
    }


def public_plan_payload(plan: SubscriptionPlan) -> dict:
    return _plan_payload(plan)

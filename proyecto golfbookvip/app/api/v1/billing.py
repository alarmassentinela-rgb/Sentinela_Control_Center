from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import DB
from app.models.subscription import SubscriptionPlan
from app.services.plans import public_plan_payload

router = APIRouter()


@router.get("/plans")
async def list_billing_plans(db: DB):
    result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active == True)
        .order_by(SubscriptionPlan.plan_type, SubscriptionPlan.price_monthly, SubscriptionPlan.id)
    )
    player: list[dict] = []
    club: list[dict] = []
    for plan in result.scalars().all():
        payload = public_plan_payload(plan)
        if plan.plan_type == "player":
            player.append(payload)
        elif plan.plan_type == "club":
            club.append(payload)
    return {"player": player, "club": club}

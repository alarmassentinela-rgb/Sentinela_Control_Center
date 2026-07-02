import uuid
from decimal import Decimal
from typing import Literal, Optional

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.api.v1.auth import limiter
from app.api.v1.clubs import _require_club_role
from app.core.config import settings
from app.core.deps import CurrentUser, DB
from app.models.club import Club
from app.models.subscription import SubscriptionPlan
from app.services.plans import public_plan_payload

router = APIRouter()
stripe.api_key = settings.STRIPE_SECRET_KEY


class CheckoutRequest(BaseModel):
    plan_code: str
    cycle: Literal["monthly", "yearly"]
    club_id: Optional[uuid.UUID] = None


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


@router.post("/checkout")
@limiter.limit("20/minute")
async def create_checkout_session(
    request: Request,
    payload: CheckoutRequest,
    current_user: CurrentUser,
    db: DB,
):
    plan = await db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.code == payload.plan_code,
            SubscriptionPlan.is_active == True,
        )
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    price = plan.price_yearly if payload.cycle == "yearly" else plan.price_monthly
    price_dec = Decimal(str(price or 0))
    if price_dec <= 0:
        raise HTTPException(status_code=400, detail="Ese plan no requiere pago")

    club = None
    scope = "user"
    if plan.plan_type == "club":
        if not payload.club_id:
            raise HTTPException(status_code=422, detail="club_id es requerido para planes de club")
        await _require_club_role(db, payload.club_id, current_user, "admin")
        club = await db.scalar(select(Club).where(Club.id == payload.club_id, Club.is_active == True))
        if not club:
            raise HTTPException(status_code=404, detail="Club no encontrado")
        scope = "club"
    elif plan.plan_type != "player":
        raise HTTPException(status_code=400, detail="Tipo de plan inválido")

    unit_amount = int((price_dec * Decimal("100")).quantize(Decimal("1")))
    frontend = settings.FRONTEND_URL.rstrip("/")

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{
                "price_data": {
                    "currency": (club.currency.lower() if club else "usd"),
                    "product_data": {"name": plan.name},
                    "unit_amount": unit_amount,
                    "recurring": {"interval": "year" if payload.cycle == "yearly" else "month"},
                },
                "quantity": 1,
            }],
            customer_email=current_user.email,
            metadata={
                "scope": scope,
                "user_id": str(current_user.id),
                "club_id": str(payload.club_id) if payload.club_id else "",
                "target_plan_id": str(plan.id),
                "target_plan_code": plan.code,
                "cycle": payload.cycle,
            },
            success_url=f"{frontend}/es/billing?status=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend}/es/billing?status=cancel",
            client_reference_id=str(current_user.id),
        )
    except stripe.error.StripeError:
        raise HTTPException(status_code=502, detail="No se pudo iniciar Stripe Checkout")

    checkout_url = session.get("url") if hasattr(session, "get") else session.url
    return {"checkout_url": checkout_url}

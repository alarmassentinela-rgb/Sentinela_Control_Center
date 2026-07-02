"""
Stripe Webhook Handler
Endpoint: POST /api/v1/stripe/webhook

Eventos manejados:
  - payment_intent.succeeded
  - customer.subscription.updated
  - customer.subscription.deleted
  - invoice.paid
  - invoice.payment_failed
"""
import stripe
from fastapi import APIRouter, Request, HTTPException, Header
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.subscription import UserSubscription, ClubSubscription
from app.models.payment import Invoice, ProcessedStripeEvent
from app.models.user import User
from app.models.club import Club

router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Firma inválida")
    except Exception:
        raise HTTPException(status_code=400, detail="Payload inválido")

    async with AsyncSessionLocal() as db:
        event_id = event.get("id")
        event_type = event["type"]
        data = event["data"]["object"]
        if event_id:
            inserted_event = await db.execute(
                insert(ProcessedStripeEvent)
                .values(event_id=event_id)
                .on_conflict_do_nothing(index_elements=["event_id"])
                .returning(ProcessedStripeEvent.event_id)
            )
            if inserted_event.scalar_one_or_none() is None:
                await db.rollback()
                return {"status": "duplicate", "event": event_type}

        # ── payment_intent.succeeded ─────────────────────────────────
        if event_type == "payment_intent.succeeded":
            await _handle_payment_intent_succeeded(db, data)

        # ── customer.subscription.updated ────────────────────────────
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(db, data)

        # ── customer.subscription.deleted ────────────────────────────
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(db, data)

        # ── invoice.paid ─────────────────────────────────────────────
        elif event_type == "invoice.paid":
            await _handle_invoice_paid(db, data)

        # ── invoice.payment_failed ────────────────────────────────────
        elif event_type == "invoice.payment_failed":
            await _handle_invoice_payment_failed(db, data)

        await db.commit()

    return {"status": "ok", "event": event_type}


# ── Handlers internos ────────────────────────────────────────────────────────

async def _handle_payment_intent_succeeded(db, pi: dict):
    """Registra el pago como Invoice en la BD."""
    metadata = pi.get("metadata", {})
    user_id = metadata.get("user_id")
    club_id = metadata.get("club_id")
    amount = (Decimal(pi["amount"]) / Decimal(100)).quantize(Decimal("0.01"))
    description = metadata.get("description") or f"Pago GolfBookVIP · PaymentIntent {pi.get('id')}"

    db.add(Invoice(
        user_id=user_id,
        club_id=club_id,
        stripe_invoice_id=None,
        amount=amount,
        currency=pi.get("currency", "usd").upper(),
        status="paid",
        description=description,
        paid_at=datetime.now(timezone.utc),
    ))


async def _insert_invoice_if_new(db, values: dict) -> None:
    stripe_invoice_id = values.get("stripe_invoice_id")
    if stripe_invoice_id:
        await db.execute(
            insert(Invoice)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["stripe_invoice_id"])
        )
        return
    db.add(Invoice(**values))


async def _handle_subscription_updated(db, sub: dict):
    """Sincroniza estado de la suscripción (usuario o club)."""
    stripe_sub_id = sub["id"]
    status = _map_stripe_status(sub["status"])
    period_start = datetime.fromtimestamp(sub["current_period_start"], tz=timezone.utc)
    period_end = datetime.fromtimestamp(sub["current_period_end"], tz=timezone.utc)

    # Intentar en user_subscriptions primero
    result = await db.execute(
        select(UserSubscription).where(UserSubscription.stripe_sub_id == stripe_sub_id)
    )
    user_sub = result.scalar_one_or_none()
    if user_sub:
        user_sub.status = status
        user_sub.current_period_start = period_start
        user_sub.current_period_end = period_end
        # Sincronizar en tabla users
        await db.execute(
            update(User)
            .where(User.id == user_sub.user_id)
            .values(plan_expires_at=period_end)
        )
        return

    # Buscar en club_subscriptions
    result = await db.execute(
        select(ClubSubscription).where(ClubSubscription.stripe_sub_id == stripe_sub_id)
    )
    club_sub = result.scalar_one_or_none()
    if club_sub:
        club_sub.status = status
        club_sub.current_period_start = period_start
        club_sub.current_period_end = period_end
        await db.execute(
            update(Club)
            .where(Club.id == club_sub.club_id)
            .values(plan_expires_at=period_end)
        )


async def _handle_subscription_deleted(db, sub: dict):
    """Marca la suscripción como cancelada."""
    stripe_sub_id = sub["id"]
    cancelled_at = datetime.now(timezone.utc)

    result = await db.execute(
        select(UserSubscription).where(UserSubscription.stripe_sub_id == stripe_sub_id)
    )
    user_sub = result.scalar_one_or_none()
    if user_sub:
        user_sub.status = "cancelled"
        user_sub.cancelled_at = cancelled_at
        return

    result = await db.execute(
        select(ClubSubscription).where(ClubSubscription.stripe_sub_id == stripe_sub_id)
    )
    club_sub = result.scalar_one_or_none()
    if club_sub:
        club_sub.status = "cancelled"
        club_sub.cancelled_at = cancelled_at


async def _handle_invoice_paid(db, inv: dict):
    """Registra la factura pagada y actualiza la suscripción."""
    stripe_sub_id = inv.get("subscription")
    stripe_inv_id = inv.get("id")

    # Buscar a quién pertenece
    user_id = club_id = None
    if stripe_sub_id:
        result = await db.execute(
            select(UserSubscription).where(UserSubscription.stripe_sub_id == stripe_sub_id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            user_id = sub.user_id
            sub.status = "active"
        else:
            result = await db.execute(
                select(ClubSubscription).where(ClubSubscription.stripe_sub_id == stripe_sub_id)
            )
            club_sub = result.scalar_one_or_none()
            if club_sub:
                club_id = club_sub.club_id
                club_sub.status = "active"

    amount = (Decimal(inv["amount_paid"]) / Decimal(100)).quantize(Decimal("0.01"))
    await _insert_invoice_if_new(db, dict(
        user_id=user_id,
        club_id=club_id,
        stripe_invoice_id=stripe_inv_id,
        amount=amount,
        currency=inv.get("currency", "usd").upper(),
        status="paid",
        description=f"Suscripción GolfBookVIP — {inv.get('period_start', '')}",
        paid_at=datetime.now(timezone.utc),
    ))


async def _handle_invoice_payment_failed(db, inv: dict):
    """Marca la suscripción como past_due."""
    stripe_sub_id = inv.get("subscription")
    if not stripe_sub_id:
        return

    result = await db.execute(
        select(UserSubscription).where(UserSubscription.stripe_sub_id == stripe_sub_id)
    )
    user_sub = result.scalar_one_or_none()
    if user_sub:
        user_sub.status = "past_due"
        return

    result = await db.execute(
        select(ClubSubscription).where(ClubSubscription.stripe_sub_id == stripe_sub_id)
    )
    club_sub = result.scalar_one_or_none()
    if club_sub:
        club_sub.status = "past_due"


def _map_stripe_status(stripe_status: str) -> str:
    return {
        "active": "active",
        "trialing": "trial",
        "past_due": "past_due",
        "canceled": "cancelled",
        "incomplete": "past_due",
        "incomplete_expired": "expired",
        "unpaid": "past_due",
    }.get(stripe_status, "active")

"""stripe idempotency

Revision ID: 0003_stripe_idempotency
Revises: 0002_seed_plans
Create Date: 2026-07-01
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_stripe_idempotency"
down_revision = "0002_seed_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_stripe_events",
        sa.Column("event_id", sa.String(length=200), nullable=False),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_unique_constraint(
        "uq_invoices_stripe_invoice_id",
        "invoices",
        ["stripe_invoice_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_invoices_stripe_invoice_id", "invoices", type_="unique")
    op.drop_table("processed_stripe_events")

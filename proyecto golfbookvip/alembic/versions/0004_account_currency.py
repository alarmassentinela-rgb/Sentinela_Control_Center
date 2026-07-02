"""account currency

Revision ID: 0004_account_currency
Revises: 0003_stripe_idempotency
Create Date: 2026-07-02
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_account_currency"
down_revision = "0003_stripe_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("member_accounts", sa.Column("currency", sa.String(length=10), nullable=True))
    op.add_column("account_transactions", sa.Column("currency", sa.String(length=10), nullable=True))

    op.execute(
        """
        UPDATE member_accounts a
        SET currency = c.currency
        FROM clubs c
        WHERE a.club_id = c.id
          AND a.currency IS NULL
        """
    )
    op.execute("UPDATE member_accounts SET currency = 'USD' WHERE currency IS NULL")
    op.execute(
        """
        UPDATE account_transactions t
        SET currency = a.currency
        FROM member_accounts a
        WHERE t.account_id = a.id
          AND t.currency IS NULL
        """
    )
    op.execute("UPDATE account_transactions SET currency = 'USD' WHERE currency IS NULL")


def downgrade() -> None:
    op.drop_column("account_transactions", "currency")
    op.drop_column("member_accounts", "currency")

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.models.club import AccountTransaction, MemberAccount


CHARGE_TYPES = {"charge", "membership_fee", "green_fee", "bet_loss"}
CREDIT_TYPES = {"payment", "credit", "refund", "bet_win"}


def _signed_delta(tx: AccountTransaction) -> Decimal:
    amount = Decimal(str(tx.amount or 0)).quantize(Decimal("0.01"))
    if tx.type in CREDIT_TYPES:
        return amount
    if tx.type in CHARGE_TYPES:
        return -amount
    if tx.type == "other":
        return amount
    return Decimal("0.00")


async def reconcile_account_balance(db, account_id: UUID) -> tuple[bool, Decimal, Decimal]:
    account = await db.scalar(select(MemberAccount).where(MemberAccount.id == account_id))
    if not account:
        raise ValueError(f"Account not found: {account_id}")

    result = await db.execute(
        select(AccountTransaction).where(AccountTransaction.account_id == account_id)
    )
    expected = sum((_signed_delta(tx) for tx in result.scalars().all()), Decimal("0.00"))
    expected = expected.quantize(Decimal("0.01"))
    actual = Decimal(str(account.balance or 0)).quantize(Decimal("0.01"))
    return expected == actual, expected, actual

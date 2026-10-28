from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.domain.money import parse_money, require_usd


class TransactionKind(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    REFUND = "refund"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"


class TransactionStatus(StrEnum):
    PENDING = "pending"
    POSTED = "posted"
    VOIDED = "voided"


POSITIVE_KINDS = frozenset(
    {TransactionKind.INCOME, TransactionKind.REFUND, TransactionKind.TRANSFER_IN}
)
NEGATIVE_KINDS = frozenset({TransactionKind.EXPENSE, TransactionKind.TRANSFER_OUT})


def validate_transaction(
    amount: str | int | Decimal, kind: TransactionKind, currency: str = "USD"
) -> Decimal:
    kind = TransactionKind(kind)
    require_usd(currency)
    parsed = parse_money(amount)
    if parsed == 0:
        raise ValueError("Transaction amount must be nonzero")
    if kind in POSITIVE_KINDS and parsed < 0:
        raise ValueError(f"{kind} must have a positive amount")
    if kind in NEGATIVE_KINDS and parsed > 0:
        raise ValueError(f"{kind} must have a negative amount")
    return parsed


def validate_date_range(start_date: date, end_date: date) -> None:
    if start_date >= end_date:
        raise ValueError("start_date must precede end_date")


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end

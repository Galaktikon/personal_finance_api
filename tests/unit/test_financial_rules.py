from datetime import date
from decimal import Decimal

import pytest

from app.domain.money import money_string, parse_money, require_usd
from app.domain.transactions import (
    TransactionKind,
    month_bounds,
    validate_date_range,
    validate_transaction,
)
from app.domain.transfers import validate_transfer_pair


@pytest.mark.parametrize(
    ("source", "expected"),
    [("12", Decimal("12.00")), ("-0.25", Decimal("-0.25")), (Decimal("0.1"), Decimal("0.10"))],
)
def test_money_parsing(source: str | Decimal, expected: Decimal) -> None:
    assert parse_money(source) == expected
    assert money_string(expected) == format(expected, ".2f")


@pytest.mark.parametrize(
    "source",
    [1.23, True, "1.234", Decimal("1.230"), "NaN", "Infinity", "", "100000000000000000"],
)
def test_money_rejects_unsupported_values(source: object) -> None:
    with pytest.raises(ValueError):
        parse_money(source)  # type: ignore[arg-type]


def test_usd_only() -> None:
    assert require_usd("USD") == "USD"
    with pytest.raises(ValueError):
        require_usd("EUR")


@pytest.mark.parametrize(
    ("kind", "amount"),
    [
        (TransactionKind.INCOME, "1.00"),
        (TransactionKind.EXPENSE, "-1.00"),
        (TransactionKind.REFUND, "1.00"),
        (TransactionKind.TRANSFER_OUT, "-1.00"),
        (TransactionKind.TRANSFER_IN, "1.00"),
    ],
)
def test_transaction_signs(kind: TransactionKind, amount: str) -> None:
    assert validate_transaction(amount, kind) == Decimal(amount)
    with pytest.raises(ValueError):
        validate_transaction(-Decimal(amount), kind)


def test_zero_and_wrong_currency_rejected() -> None:
    with pytest.raises(ValueError):
        validate_transaction("0", TransactionKind.INCOME)
    with pytest.raises(ValueError):
        validate_transaction("1", TransactionKind.INCOME, "EUR")


def test_transfer_pair_must_cancel_between_distinct_accounts() -> None:
    validate_transfer_pair(
        Decimal("-25.00"),
        Decimal("25.00"),
        TransactionKind.TRANSFER_OUT,
        TransactionKind.TRANSFER_IN,
        "a",
        "b",
    )
    with pytest.raises(ValueError):
        validate_transfer_pair(
            Decimal("-25.00"),
            Decimal("24.99"),
            TransactionKind.TRANSFER_OUT,
            TransactionKind.TRANSFER_IN,
            "a",
            "b",
        )
    with pytest.raises(ValueError):
        validate_transfer_pair(
            Decimal("-25.00"),
            Decimal("25.00"),
            TransactionKind.TRANSFER_OUT,
            TransactionKind.TRANSFER_IN,
            "a",
            "a",
        )


def test_half_open_month_boundaries_and_leap_year() -> None:
    assert month_bounds(2024, 2) == (date(2024, 2, 1), date(2024, 3, 1))
    assert month_bounds(2026, 12) == (date(2026, 12, 1), date(2027, 1, 1))
    validate_date_range(date(2024, 2, 1), date(2024, 3, 1))
    with pytest.raises(ValueError):
        validate_date_range(date(2024, 3, 1), date(2024, 3, 1))

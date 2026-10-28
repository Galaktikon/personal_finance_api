from decimal import Decimal, InvalidOperation

CENT = Decimal("0.01")
MAX_ABS_AMOUNT = Decimal("100000000000000000")  # NUMERIC(19,2): 17 integral digits.


def parse_money(value: str | int | Decimal) -> Decimal:
    """Parse USD money without rounding or binary floating-point conversion."""
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("Money must be a decimal string, integer, or Decimal")
    if isinstance(value, str) and not value.strip():
        raise ValueError("Money cannot be empty")
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid monetary amount") from exc
    if not amount.is_finite():
        raise ValueError("Money must be finite")
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise ValueError("Money supports at most two fractional digits")
    if abs(amount) >= MAX_ABS_AMOUNT:
        raise ValueError("Money exceeds NUMERIC(19,2) range")
    return amount.quantize(CENT)


def money_string(amount: Decimal) -> str:
    return format(parse_money(amount), ".2f")


def require_usd(currency: str) -> str:
    if currency != "USD":
        raise ValueError("Only USD is supported")
    return currency

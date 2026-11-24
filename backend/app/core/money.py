from decimal import Decimal, ROUND_HALF_UP

MONEY = Decimal("0.01")


def q(value: Decimal | int | str | float) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{q(value):.2f}"

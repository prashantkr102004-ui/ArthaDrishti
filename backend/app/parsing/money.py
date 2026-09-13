import re
from decimal import Decimal, InvalidOperation

from app.parsing.exceptions import ParsingError

MONEY_PATTERN = re.compile(r"^\d+(?:\.\d{1,2})?$")


def parse_money(value: str | None, *, required: bool = True) -> Decimal | None:
    raw_value = (value or "").strip()
    if not raw_value:
        if required:
            raise ParsingError("invalid_amount", "Amount is required.")
        return None

    cleaned = (
        raw_value.replace(",", "")
        .replace("\u20b9", "")
        .replace("INR", "")
        .strip()
    )
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]

    if cleaned.startswith("-"):
        raise ParsingError("invalid_amount", "Amounts must be positive.")
    if not MONEY_PATTERN.fullmatch(cleaned):
        raise ParsingError("invalid_amount", f"Invalid amount: {raw_value}")

    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ParsingError("invalid_amount", f"Invalid amount: {raw_value}") from exc

    if required and amount <= 0:
        raise ParsingError("invalid_amount", "Amount must be greater than zero.")
    return amount

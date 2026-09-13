from datetime import date, datetime

from app.parsing.exceptions import ParsingError

SUPPORTED_DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y")


def parse_statement_date(value: str) -> date:
    raw_value = value.strip()
    for date_format in SUPPORTED_DATE_FORMATS:
        try:
            return datetime.strptime(raw_value, date_format).date()
        except ValueError:
            continue

    raise ParsingError("invalid_date", f"Invalid date: {value}")

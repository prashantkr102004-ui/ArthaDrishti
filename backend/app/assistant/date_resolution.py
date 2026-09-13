import re
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta

from app.services.analytics import DateRange

MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


@dataclass(frozen=True)
class ResolvedPeriods:
    primary: DateRange
    comparison: DateRange | None = None


def resolve_periods(question: str, today: date | None = None) -> ResolvedPeriods:
    current = today or date.today()
    normalized = question.casefold()

    explicit_month = _month_from_text(normalized)
    if explicit_month is not None:
        return ResolvedPeriods(primary=_calendar_month(current.year, explicit_month))

    if "yesterday" in normalized:
        yesterday = current - timedelta(days=1)
        return ResolvedPeriods(primary=DateRange(yesterday, yesterday))

    if "this year" in normalized:
        return ResolvedPeriods(primary=DateRange(date(current.year, 1, 1), date(current.year, 12, 31)))

    if "last 6 months" in normalized or "last six months" in normalized:
        return ResolvedPeriods(primary=_month_window(current, 6))

    if "last 3 months" in normalized or "last three months" in normalized:
        return ResolvedPeriods(primary=_month_window(current, 3))

    if "last month" in normalized:
        return ResolvedPeriods(primary=_relative_month(current, -1))

    this_month = _relative_month(current, 0)
    last_month = _relative_month(current, -1)
    if "compare" in normalized or "higher" in normalized or "more" in normalized:
        return ResolvedPeriods(primary=this_month, comparison=last_month)

    return ResolvedPeriods(primary=this_month)


def _month_window(today: date, months: int) -> DateRange:
    start_month_index = today.month - months + 1
    start_year = today.year
    while start_month_index <= 0:
        start_month_index += 12
        start_year -= 1
    return DateRange(
        start_date=date(start_year, start_month_index, 1),
        end_date=date(today.year, today.month, monthrange(today.year, today.month)[1]),
    )


def _relative_month(today: date, offset: int) -> DateRange:
    month = today.month + offset
    year = today.year
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return _calendar_month(year, month)


def _calendar_month(year: int, month: int) -> DateRange:
    return DateRange(
        start_date=date(year, month, 1),
        end_date=date(year, month, monthrange(year, month)[1]),
    )


def _month_from_text(text: str) -> int | None:
    for month_name, month_number in MONTH_NAMES.items():
        if re.search(rf"\b{month_name}\b", text):
            return month_number
    return None

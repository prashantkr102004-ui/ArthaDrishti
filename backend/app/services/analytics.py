from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsPeriod,
    AnalyticsSummaryResponse,
    CategoryDeltaItem,
    CategorySpendingItem,
    CategorySpendingResponse,
    MerchantSpendingItem,
    MerchantSpendingResponse,
    MonthlyAnalyticsItem,
    MonthlyAnalyticsResponse,
    PeriodComparisonResponse,
)

MONEY_QUANT = Decimal("0.0001")
PERCENT_QUANT = Decimal("0.0001")
ZERO = Decimal("0.0000")
ONE_HUNDRED = Decimal("100")

INCOME_SLUGS = {"income"}
TRANSFER_SLUGS = {"transfers"}
INVESTMENT_SLUGS = {"investments"}
NON_EXPENSE_SLUGS = INCOME_SLUGS | TRANSFER_SLUGS | INVESTMENT_SLUGS


@dataclass(frozen=True)
class DateRange:
    start_date: date
    end_date: date


def get_financial_summary(
    db: Session,
    current_user: User,
    period: DateRange,
) -> AnalyticsSummaryResponse:
    income_expr = _sum_when(_is_income(), Transaction.amount)
    expense_expr = _sum_when(_is_expense(), Transaction.amount)
    investments_expr = _sum_when(_is_investment(), Transaction.amount)
    debit_expr = _sum_when(Transaction.direction == "debit", Transaction.amount)
    credit_expr = _sum_when(Transaction.direction == "credit", Transaction.amount)

    row = db.execute(
        select(
            income_expr.label("total_income"),
            expense_expr.label("total_expenses"),
            investments_expr.label("investment_amount"),
            debit_expr.label("total_debits"),
            credit_expr.label("total_credits"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .select_from(Transaction)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(*_base_filters(current_user, period))
    ).one()

    total_income = _money(row.total_income)
    total_expenses = _money(row.total_expenses)
    total_debits = _money(row.total_debits)
    total_credits = _money(row.total_credits)
    investment_amount = _money(row.investment_amount)
    savings = _money(total_income - total_expenses)

    return AnalyticsSummaryResponse(
        start_date=period.start_date,
        end_date=period.end_date,
        total_income=total_income,
        total_expenses=total_expenses,
        savings=savings,
        savings_rate_percent=_percentage(savings, total_income),
        total_debits=total_debits,
        total_credits=total_credits,
        raw_net_flow=_money(total_credits - total_debits),
        investment_amount=investment_amount,
        transaction_count=int(row.transaction_count or 0),
    )


def get_category_spending(
    db: Session,
    current_user: User,
    period: DateRange,
) -> CategorySpendingResponse:
    rows = db.execute(
        select(
            Transaction.category_id,
            func.coalesce(Category.name, "Uncategorized").label("category_name"),
            _sum_amount().label("amount"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .select_from(Transaction)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(*_base_filters(current_user, period), _is_expense())
        .group_by(Transaction.category_id, Category.name)
        .order_by(func.sum(Transaction.amount).desc(), func.coalesce(Category.name, "Uncategorized").asc())
    ).all()

    total_expenses = _money(sum((_money(row.amount) for row in rows), ZERO))
    items = [
        CategorySpendingItem(
            category_id=row.category_id,
            category_name=row.category_name,
            amount=_money(row.amount),
            transaction_count=int(row.transaction_count or 0),
            percentage_of_total_expenses=_percentage(_money(row.amount), total_expenses) or ZERO,
        )
        for row in rows
    ]
    return CategorySpendingResponse(
        start_date=period.start_date,
        end_date=period.end_date,
        total_expenses=total_expenses,
        items=items,
    )


def get_monthly_analytics(
    db: Session,
    current_user: User,
    period: DateRange,
) -> MonthlyAnalyticsResponse:
    month_expr = func.to_char(func.date_trunc("month", Transaction.transaction_date), "YYYY-MM")
    rows = db.execute(
        select(
            month_expr.label("month"),
            _sum_when(_is_income(), Transaction.amount).label("income"),
            _sum_when(_is_expense(), Transaction.amount).label("expenses"),
            _sum_when(_is_investment(), Transaction.amount).label("investments"),
            _sum_when(Transaction.direction == "debit", Transaction.amount).label("total_debits"),
            _sum_when(Transaction.direction == "credit", Transaction.amount).label("total_credits"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .select_from(Transaction)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(*_base_filters(current_user, period))
        .group_by(month_expr)
        .order_by(month_expr.asc())
    ).all()

    items: list[MonthlyAnalyticsItem] = []
    for row in rows:
        income = _money(row.income)
        expenses = _money(row.expenses)
        total_debits = _money(row.total_debits)
        total_credits = _money(row.total_credits)
        items.append(
            MonthlyAnalyticsItem(
                month=row.month,
                income=income,
                expenses=expenses,
                savings=_money(income - expenses),
                investments=_money(row.investments),
                total_debits=total_debits,
                total_credits=total_credits,
                raw_net_flow=_money(total_credits - total_debits),
                transaction_count=int(row.transaction_count or 0),
            )
        )

    return MonthlyAnalyticsResponse(
        start_date=period.start_date,
        end_date=period.end_date,
        items=items,
    )


def get_top_merchants(
    db: Session,
    current_user: User,
    period: DateRange,
    limit: int,
) -> MerchantSpendingResponse:
    merchant_expr = func.coalesce(Transaction.canonical_merchant, "Unknown merchant")
    rows = db.execute(
        select(
            merchant_expr.label("merchant_name"),
            _sum_amount().label("amount"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .select_from(Transaction)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(*_base_filters(current_user, period), _is_expense())
        .group_by(merchant_expr)
        .order_by(func.sum(Transaction.amount).desc(), merchant_expr.asc())
        .limit(limit)
    ).all()

    return MerchantSpendingResponse(
        start_date=period.start_date,
        end_date=period.end_date,
        items=[
            MerchantSpendingItem(
                merchant_name=row.merchant_name,
                amount=_money(row.amount),
                transaction_count=int(row.transaction_count or 0),
            )
            for row in rows
        ],
    )


def compare_periods(
    db: Session,
    current_user: User,
    period_a: DateRange,
    period_b: DateRange,
) -> PeriodComparisonResponse:
    summary_a = get_financial_summary(db, current_user, period_a)
    summary_b = get_financial_summary(db, current_user, period_b)
    categories_a = _category_amounts(db, current_user, period_a)
    categories_b = _category_amounts(db, current_user, period_b)

    category_keys = set(categories_a) | set(categories_b)
    category_deltas = [
        _category_delta(key, categories_a.get(key), categories_b.get(key))
        for key in category_keys
    ]
    category_deltas.sort(
        key=lambda item: (
            item.difference <= ZERO,
            -abs(item.difference),
            item.category_name,
        )
    )

    expense_difference = _money(summary_a.total_expenses - summary_b.total_expenses)

    return PeriodComparisonResponse(
        period_a=AnalyticsPeriod(start_date=period_a.start_date, end_date=period_a.end_date),
        period_b=AnalyticsPeriod(start_date=period_b.start_date, end_date=period_b.end_date),
        expense_period_a=summary_a.total_expenses,
        expense_period_b=summary_b.total_expenses,
        expense_difference=expense_difference,
        expense_percentage_change=_percentage(expense_difference, summary_b.total_expenses),
        income_period_a=summary_a.total_income,
        income_period_b=summary_b.total_income,
        income_difference=_money(summary_a.total_income - summary_b.total_income),
        savings_period_a=summary_a.savings,
        savings_period_b=summary_b.savings,
        savings_difference=_money(summary_a.savings - summary_b.savings),
        category_deltas=category_deltas,
    )


def _category_amounts(
    db: Session,
    current_user: User,
    period: DateRange,
) -> dict[tuple[UUID | None, str], Decimal]:
    response = get_category_spending(db, current_user, period)
    return {
        (item.category_id, item.category_name): item.amount
        for item in response.items
    }


def _category_delta(
    key: tuple[UUID | None, str],
    amount_a: Decimal | None,
    amount_b: Decimal | None,
) -> CategoryDeltaItem:
    period_a_amount = amount_a or ZERO
    period_b_amount = amount_b or ZERO
    difference = _money(period_a_amount - period_b_amount)
    return CategoryDeltaItem(
        category_id=key[0],
        category_name=key[1],
        amount_period_a=period_a_amount,
        amount_period_b=period_b_amount,
        difference=difference,
        percentage_change=_percentage(difference, period_b_amount),
    )


def _base_filters(current_user: User, period: DateRange) -> list[object]:
    return [
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= period.start_date,
        Transaction.transaction_date <= period.end_date,
    ]


def _is_income():
    return (Transaction.direction == "credit") & Category.slug.in_(INCOME_SLUGS)


def _is_investment():
    return (Transaction.direction == "debit") & Category.slug.in_(INVESTMENT_SLUGS)


def _is_expense():
    return (Transaction.direction == "debit") & (
        or_(Category.slug.is_(None), Category.slug.notin_(NON_EXPENSE_SLUGS))
    )


def _sum_amount():
    return func.coalesce(func.sum(Transaction.amount), ZERO)


def _sum_when(condition, value):
    return func.coalesce(func.sum(case((condition, value), else_=ZERO)), ZERO)


def _money(value: Decimal | int | None) -> Decimal:
    return Decimal(value or ZERO).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _percentage(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == ZERO:
        return None
    return ((numerator / denominator) * ONE_HUNDRED).quantize(
        PERCENT_QUANT,
        rounding=ROUND_HALF_UP,
    )

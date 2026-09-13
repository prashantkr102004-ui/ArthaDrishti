from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class AnalyticsPeriod(BaseModel):
    start_date: date
    end_date: date


class AnalyticsSummaryResponse(BaseModel):
    start_date: date
    end_date: date
    total_income: Decimal
    total_expenses: Decimal
    savings: Decimal
    savings_rate_percent: Decimal | None
    total_debits: Decimal
    total_credits: Decimal
    raw_net_flow: Decimal
    investment_amount: Decimal
    transaction_count: int


class CategorySpendingItem(BaseModel):
    category_id: UUID | None
    category_name: str
    amount: Decimal
    transaction_count: int
    percentage_of_total_expenses: Decimal


class CategorySpendingResponse(BaseModel):
    start_date: date
    end_date: date
    total_expenses: Decimal
    items: list[CategorySpendingItem]


class MonthlyAnalyticsItem(BaseModel):
    month: str
    income: Decimal
    expenses: Decimal
    savings: Decimal
    investments: Decimal
    total_debits: Decimal
    total_credits: Decimal
    raw_net_flow: Decimal
    transaction_count: int


class MonthlyAnalyticsResponse(BaseModel):
    start_date: date
    end_date: date
    items: list[MonthlyAnalyticsItem]


class MerchantSpendingItem(BaseModel):
    merchant_name: str
    amount: Decimal
    transaction_count: int


class MerchantSpendingResponse(BaseModel):
    start_date: date
    end_date: date
    items: list[MerchantSpendingItem]


class CategoryDeltaItem(BaseModel):
    category_id: UUID | None
    category_name: str
    amount_period_a: Decimal
    amount_period_b: Decimal
    difference: Decimal
    percentage_change: Decimal | None


class PeriodComparisonResponse(BaseModel):
    period_a: AnalyticsPeriod
    period_b: AnalyticsPeriod
    expense_period_a: Decimal
    expense_period_b: Decimal
    expense_difference: Decimal
    expense_percentage_change: Decimal | None
    income_period_a: Decimal
    income_period_b: Decimal
    income_difference: Decimal
    savings_period_a: Decimal
    savings_period_b: Decimal
    savings_difference: Decimal
    category_deltas: list[CategoryDeltaItem]

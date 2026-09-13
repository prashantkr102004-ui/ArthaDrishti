from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel

from app.schemas.budget import BudgetProgressItem


class RecurrenceFrequency(StrEnum):
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"


class RecurringStatus(StrEnum):
    active = "active"
    possibly_inactive = "possibly_inactive"


class RecurringPaymentItem(BaseModel):
    merchant: str
    category_name: str | None
    frequency: RecurrenceFrequency
    occurrence_count: int
    average_amount: Decimal
    min_amount: Decimal
    max_amount: Decimal
    first_seen: date
    last_seen: date
    predicted_next_date: date | None
    confidence: Decimal
    status: RecurringStatus
    is_subscription: bool
    explanation: str


class RecurringPaymentsResponse(BaseModel):
    items: list[RecurringPaymentItem]


class SubscriptionItem(BaseModel):
    merchant: str
    category_name: str | None
    typical_amount: Decimal
    billing_frequency: RecurrenceFrequency
    estimated_monthly_cost: Decimal
    last_charged_date: date
    estimated_next_charge: date | None
    total_spent: Decimal
    confidence: Decimal
    status: RecurringStatus


class SubscriptionsResponse(BaseModel):
    total_estimated_monthly_cost: Decimal
    items: list[SubscriptionItem]


class ForecastStatus(StrEnum):
    ready = "ready"
    insufficient_history = "insufficient_history"


class SpendingForecastResponse(BaseModel):
    status: ForecastStatus
    method: str
    months_used: int
    history_required_months: int
    months_missing: int
    projected_next_month_expenses: Decimal | None
    lower_estimate: Decimal | None
    upper_estimate: Decimal | None
    explanation: str


class AnomalyItem(BaseModel):
    transaction_id: str
    transaction_date: date
    merchant: str | None
    category_name: str | None
    amount: Decimal
    direction: str
    method: str
    score: Decimal
    reason: str


class AnomaliesResponse(BaseModel):
    items: list[AnomalyItem]


class InsightItem(BaseModel):
    type: str
    title: str
    detail: str
    severity: str


class AdvancedInsightsResponse(BaseModel):
    recurring_payments: list[RecurringPaymentItem]
    subscriptions: list[SubscriptionItem]
    subscription_total_estimated_monthly_cost: Decimal
    budgets: list[BudgetProgressItem]
    forecast: SpendingForecastResponse
    anomalies: list[AnomalyItem]
    insights: list[InsightItem]

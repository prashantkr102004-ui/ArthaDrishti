from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.advanced import (
    AdvancedInsightsResponse,
    AnomaliesResponse,
    AnomalyItem,
    ForecastStatus,
    InsightItem,
    RecurrenceFrequency,
    RecurringPaymentItem,
    RecurringPaymentsResponse,
    RecurringStatus,
    SpendingForecastResponse,
    SubscriptionItem,
    SubscriptionsResponse,
)
from app.services.analytics import DateRange, get_monthly_analytics
from app.services.budgets import get_budget_progress

ZERO = Decimal("0.0000")
MONEY_QUANT = Decimal("0.0001")
CONF_QUANT = Decimal("0.0001")
SUBSCRIPTION_MERCHANTS = {
    "netflix",
    "spotify",
    "prime video",
    "amazon prime",
    "youtube premium",
    "apple",
    "google",
    "microsoft",
}
NON_SUBSCRIPTION_CATEGORY_SLUGS = {"rent", "bills", "transfers", "investments", "income"}


@dataclass(frozen=True)
class AdvancedDateRange:
    start_date: date
    end_date: date


def get_recurring_payments(
    db: Session,
    current_user: User,
    today: date | None = None,
) -> RecurringPaymentsResponse:
    run_date = today or date.today()
    groups: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in _expense_like_transactions(db, current_user):
        key = _recurrence_key(transaction)
        if key:
            groups[key].append(transaction)

    items = []
    for rows in groups.values():
        rows.sort(key=lambda tx: (tx.transaction_date, tx.id))
        if len(rows) < 3:
            continue
        item = _build_recurring_item(rows, run_date)
        if item is not None:
            items.append(item)
    items.sort(key=lambda item: (-item.confidence, item.merchant))
    return RecurringPaymentsResponse(items=items)


def get_subscriptions(
    db: Session,
    current_user: User,
    today: date | None = None,
) -> SubscriptionsResponse:
    recurring = get_recurring_payments(db, current_user, today).items
    subscriptions = [
        _subscription_item(item)
        for item in recurring
        if item.is_subscription
    ]
    total = _money(sum((item.estimated_monthly_cost for item in subscriptions), ZERO))
    return SubscriptionsResponse(total_estimated_monthly_cost=total, items=subscriptions)


def forecast_spending(
    db: Session,
    current_user: User,
    today: date | None = None,
    months: int = 6,
) -> SpendingForecastResponse:
    required_months = 3
    run_date = today or date.today()
    current_month_start = date(run_date.year, run_date.month, 1)
    start = _month_shift(current_month_start, -months)
    monthly = get_monthly_analytics(
        db,
        current_user,
        DateRange(start_date=start, end_date=current_month_start - timedelta(days=1)),
    ).items
    expenses = [item.expenses for item in monthly]
    if len(expenses) < required_months:
        months_missing = required_months - len(expenses)
        return SpendingForecastResponse(
            status=ForecastStatus.insufficient_history,
            method="weighted_moving_average",
            months_used=len(expenses),
            history_required_months=required_months,
            months_missing=months_missing,
            projected_next_month_expenses=None,
            lower_estimate=None,
            upper_estimate=None,
            explanation=(
                f"Forecasting needs {required_months} completed months of expenses. "
                f"I found {len(expenses)}, so {months_missing} more completed "
                f"month{'s are' if months_missing != 1 else ' is'} needed."
            ),
        )

    weights = list(range(1, len(expenses) + 1))
    weighted_total = sum((amount * Decimal(weight) for amount, weight in zip(expenses, weights, strict=True)), ZERO)
    projected = _money(weighted_total / Decimal(sum(weights)))
    deviations = [abs(amount - projected) for amount in expenses]
    avg_deviation = _money(sum(deviations, ZERO) / Decimal(len(deviations)))
    return SpendingForecastResponse(
        status=ForecastStatus.ready,
        method="weighted_moving_average",
        months_used=len(expenses),
        history_required_months=required_months,
        months_missing=0,
        projected_next_month_expenses=projected,
        lower_estimate=max(_money(projected - avg_deviation), ZERO),
        upper_estimate=_money(projected + avg_deviation),
        explanation="Projection uses a weighted moving average of completed monthly expenses.",
    )


def get_financial_anomalies(
    db: Session,
    current_user: User,
    period: AdvancedDateRange | None = None,
) -> AnomaliesResponse:
    filters = [Transaction.user_id == current_user.id, Transaction.direction == "debit"]
    if period is not None:
        filters.extend([
            Transaction.transaction_date >= period.start_date,
            Transaction.transaction_date <= period.end_date,
        ])
    rows = list(
        db.scalars(
            select(Transaction)
            .options(joinedload(Transaction.category))
            .where(*filters)
            .order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
        )
    )
    history_by_merchant: dict[str, list[Decimal]] = defaultdict(list)
    anomalies: list[AnomalyItem] = []
    global_amounts: list[Decimal] = []
    for transaction in rows:
        merchant_key = transaction.merchant_key or (transaction.canonical_merchant or "").casefold()
        merchant_history = history_by_merchant[merchant_key]
        reason = None
        method = None
        score = ZERO
        if merchant_key and len(merchant_history) >= 3:
            typical = _money(sum(merchant_history, ZERO) / Decimal(len(merchant_history)))
            if typical > ZERO and transaction.amount >= typical * Decimal("3"):
                score = _money(transaction.amount / typical)
                method = "merchant_average_multiple"
                reason = (
                    f"This {transaction.currency} {transaction.amount} {transaction.canonical_merchant or 'transaction'} "
                    f"is unusually high compared with a typical {transaction.currency} {typical}."
                )
        if reason is None and len(global_amounts) >= 5:
            threshold = _robust_upper_threshold(global_amounts)
            if threshold is not None and transaction.amount > threshold:
                method = "robust_global_threshold"
                score = _money(transaction.amount - threshold)
                reason = (
                    f"This transaction is above the robust historical high-spend threshold of "
                    f"{transaction.currency} {threshold}."
                )
        if reason is not None and method is not None:
            anomalies.append(
                AnomalyItem(
                    transaction_id=str(transaction.id),
                    transaction_date=transaction.transaction_date,
                    merchant=transaction.canonical_merchant,
                    category_name=transaction.category_name,
                    amount=transaction.amount,
                    direction=transaction.direction,
                    method=method,
                    score=score,
                    reason=reason,
                )
            )
        if merchant_key:
            history_by_merchant[merchant_key].append(transaction.amount)
        global_amounts.append(transaction.amount)
    return AnomaliesResponse(items=anomalies)


def get_advanced_insights(
    db: Session,
    current_user: User,
    start_date: date,
    end_date: date,
    today: date | None = None,
) -> AdvancedInsightsResponse:
    run_date = today or date.today()
    recurring = get_recurring_payments(db, current_user, run_date).items
    subscription_response = get_subscriptions(db, current_user, run_date)
    subscriptions = subscription_response.items
    budgets = get_budget_progress(db, current_user, start_date, end_date).items
    forecast = forecast_spending(db, current_user, run_date)
    anomalies = get_financial_anomalies(db, current_user, AdvancedDateRange(start_date, end_date)).items
    insights = _build_insights(recurring, subscriptions, budgets, forecast, anomalies)
    return AdvancedInsightsResponse(
        recurring_payments=recurring,
        subscriptions=subscriptions,
        subscription_total_estimated_monthly_cost=subscription_response.total_estimated_monthly_cost,
        budgets=budgets,
        forecast=forecast,
        anomalies=anomalies,
        insights=insights,
    )


def _expense_like_transactions(db: Session, current_user: User) -> list[Transaction]:
    return list(
        db.scalars(
            select(Transaction)
            .options(joinedload(Transaction.category))
            .where(Transaction.user_id == current_user.id, Transaction.direction == "debit")
            .order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
        )
    )


def _recurrence_key(transaction: Transaction) -> str | None:
    if transaction.canonical_merchant:
        return f"merchant:{transaction.merchant_key or transaction.canonical_merchant.casefold()}"
    if transaction.normalized_description:
        return f"description:{transaction.normalized_description.casefold()}"
    return None


def _build_recurring_item(rows: list[Transaction], today: date) -> RecurringPaymentItem | None:
    intervals = [
        (rows[index].transaction_date - rows[index - 1].transaction_date).days
        for index in range(1, len(rows))
    ]
    frequency = _frequency_from_intervals(intervals)
    if frequency is None:
        return None
    amounts = [row.amount for row in rows]
    average = _money(sum(amounts, ZERO) / Decimal(len(amounts)))
    min_amount = min(amounts)
    max_amount = max(amounts)
    amount_variation = ZERO if average == ZERO else abs(max_amount - min_amount) / average
    interval_score = _interval_consistency(intervals, frequency)
    amount_score = max(Decimal("0"), Decimal("1") - amount_variation)
    count_score = min(Decimal(len(rows)) / Decimal("6"), Decimal("1"))
    confidence = (interval_score * Decimal("0.45")) + (amount_score * Decimal("0.30")) + (count_score * Decimal("0.25"))
    predicted = _predict_next_date(rows[-1].transaction_date, frequency)
    status_value = RecurringStatus.possibly_inactive if predicted and today > predicted + _frequency_tolerance(frequency) else RecurringStatus.active
    category_slug = rows[-1].category.slug if rows[-1].category else None
    is_subscription = _is_subscription(rows[-1].canonical_merchant, category_slug)
    if confidence < Decimal("0.55"):
        return None
    return RecurringPaymentItem(
        merchant=rows[-1].canonical_merchant or rows[-1].normalized_description,
        category_name=rows[-1].category_name,
        frequency=frequency,
        occurrence_count=len(rows),
        average_amount=_money(average),
        min_amount=_money(min_amount),
        max_amount=_money(max_amount),
        first_seen=rows[0].transaction_date,
        last_seen=rows[-1].transaction_date,
        predicted_next_date=predicted,
        confidence=confidence.quantize(CONF_QUANT, rounding=ROUND_HALF_UP),
        status=status_value,
        is_subscription=is_subscription,
        explanation=(
            f"Detected {len(rows)} payments with {frequency.value} timing and "
            f"typical amount {rows[-1].currency} {_money(average)}."
        ),
    )


def _frequency_from_intervals(intervals: list[int]) -> RecurrenceFrequency | None:
    if not intervals:
        return None
    midpoint = median(intervals)
    if 5 <= midpoint <= 9:
        return RecurrenceFrequency.weekly
    if 25 <= midpoint <= 35:
        return RecurrenceFrequency.monthly
    if 80 <= midpoint <= 100:
        return RecurrenceFrequency.quarterly
    if 330 <= midpoint <= 400:
        return RecurrenceFrequency.yearly
    return None


def _interval_consistency(intervals: list[int], frequency: RecurrenceFrequency) -> Decimal:
    ranges = {
        RecurrenceFrequency.weekly: (5, 9),
        RecurrenceFrequency.monthly: (25, 35),
        RecurrenceFrequency.quarterly: (80, 100),
        RecurrenceFrequency.yearly: (330, 400),
    }
    low, high = ranges[frequency]
    matches = sum(1 for interval in intervals if low <= interval <= high)
    return Decimal(matches) / Decimal(len(intervals))


def _predict_next_date(last_seen: date, frequency: RecurrenceFrequency) -> date:
    days = {
        RecurrenceFrequency.weekly: 7,
        RecurrenceFrequency.monthly: 30,
        RecurrenceFrequency.quarterly: 91,
        RecurrenceFrequency.yearly: 365,
    }[frequency]
    return last_seen + timedelta(days=days)


def _frequency_tolerance(frequency: RecurrenceFrequency) -> timedelta:
    days = {
        RecurrenceFrequency.weekly: 7,
        RecurrenceFrequency.monthly: 15,
        RecurrenceFrequency.quarterly: 30,
        RecurrenceFrequency.yearly: 45,
    }[frequency]
    return timedelta(days=days)


def _is_subscription(merchant: str | None, category_slug: str | None) -> bool:
    if category_slug in NON_SUBSCRIPTION_CATEGORY_SLUGS:
        return False
    if category_slug == "subscriptions":
        return True
    merchant_text = (merchant or "").casefold()
    return any(name in merchant_text for name in SUBSCRIPTION_MERCHANTS)


def _subscription_item(item: RecurringPaymentItem) -> SubscriptionItem:
    monthly_cost = {
        RecurrenceFrequency.weekly: item.average_amount * Decimal("4.345"),
        RecurrenceFrequency.monthly: item.average_amount,
        RecurrenceFrequency.quarterly: item.average_amount / Decimal("3"),
        RecurrenceFrequency.yearly: item.average_amount / Decimal("12"),
    }[item.frequency]
    return SubscriptionItem(
        merchant=item.merchant,
        category_name=item.category_name,
        typical_amount=item.average_amount,
        billing_frequency=item.frequency,
        estimated_monthly_cost=_money(monthly_cost),
        last_charged_date=item.last_seen,
        estimated_next_charge=item.predicted_next_date,
        total_spent=_money(item.average_amount * Decimal(item.occurrence_count)),
        confidence=item.confidence,
        status=item.status,
    )


def _robust_upper_threshold(values: list[Decimal]) -> Decimal | None:
    if len(values) < 5:
        return None
    med = Decimal(str(median(values)))
    deviations = [abs(value - med) for value in values]
    mad = Decimal(str(median(deviations)))
    if mad == ZERO:
        return max(values) * Decimal("3")
    return _money(med + Decimal("6") * mad)


def _build_insights(
    recurring: list[RecurringPaymentItem],
    subscriptions: list[SubscriptionItem],
    budgets: list,
    forecast: SpendingForecastResponse,
    anomalies: list[AnomalyItem],
) -> list[InsightItem]:
    insights: list[InsightItem] = []
    if subscriptions:
        total = _money(sum((item.estimated_monthly_cost for item in subscriptions), ZERO))
        insights.append(
            InsightItem(
                type="subscriptions",
                title="Likely subscriptions found",
                detail=f"{len(subscriptions)} subscriptions cost about INR {total} per month.",
                severity="info",
            )
        )
    exceeded = [budget for budget in budgets if budget.status.value == "exceeded"]
    if exceeded:
        insights.append(
            InsightItem(
                type="budget",
                title="Budget exceeded",
                detail=f"{len(exceeded)} budget limit is currently exceeded.",
                severity="warning",
            )
        )
    if forecast.status == ForecastStatus.ready and forecast.projected_next_month_expenses is not None:
        insights.append(
            InsightItem(
                type="forecast",
                title="Next-month spending projection",
                detail=f"Projected expenses are about INR {forecast.projected_next_month_expenses}.",
                severity="info",
            )
        )
    if anomalies:
        insights.append(
            InsightItem(
                type="anomaly",
                title="Financial anomalies detected",
                detail=f"{len(anomalies)} unusual transaction pattern was found.",
                severity="warning",
            )
        )
    if recurring and not subscriptions:
        insights.append(
            InsightItem(
                type="recurring",
                title="Recurring payments found",
                detail=f"{len(recurring)} likely recurring payment pattern was found.",
                severity="info",
            )
        )
    return insights


def _month_shift(month_start: date, months: int) -> date:
    month_index = month_start.month - 1 + months
    year = month_start.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

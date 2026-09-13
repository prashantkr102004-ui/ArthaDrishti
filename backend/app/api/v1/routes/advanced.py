from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.advanced import (
    AdvancedInsightsResponse,
    AnomaliesResponse,
    RecurringPaymentsResponse,
    SpendingForecastResponse,
    SubscriptionsResponse,
)
from app.services.advanced import (
    AdvancedDateRange,
    forecast_spending,
    get_advanced_insights,
    get_financial_anomalies,
    get_recurring_payments,
    get_subscriptions,
)

router = APIRouter(prefix="/advanced", tags=["advanced"])


@router.get("/recurring-payments", response_model=RecurringPaymentsResponse)
def recurring_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecurringPaymentsResponse:
    return get_recurring_payments(db, current_user)


@router.get("/subscriptions", response_model=SubscriptionsResponse)
def subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionsResponse:
    return get_subscriptions(db, current_user)


@router.get("/forecast", response_model=SpendingForecastResponse)
def spending_forecast(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SpendingForecastResponse:
    return forecast_spending(db, current_user)


@router.get("/anomalies", response_model=AnomaliesResponse)
def anomalies(
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnomaliesResponse:
    period = None
    if start_date is not None or end_date is not None:
        if start_date is None or end_date is None or start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Valid start_date and end_date are required.",
            )
        period = AdvancedDateRange(start_date=start_date, end_date=end_date)
    return get_financial_anomalies(db, current_user, period)


@router.get("/insights", response_model=AdvancedInsightsResponse)
def advanced_insights(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdvancedInsightsResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date must be on or before end_date.",
        )
    return get_advanced_insights(db, current_user, start_date, end_date)

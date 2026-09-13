from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    CategorySpendingResponse,
    MerchantSpendingResponse,
    MonthlyAnalyticsResponse,
    PeriodComparisonResponse,
)
from app.services.analytics import (
    DateRange,
    compare_periods,
    get_category_spending,
    get_financial_summary,
    get_monthly_analytics,
    get_top_merchants,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _date_range(start_date: date, end_date: date) -> DateRange:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date must be on or before end_date.",
        )
    return DateRange(start_date=start_date, end_date=end_date)


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def financial_summary(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyticsSummaryResponse:
    return get_financial_summary(db, current_user, _date_range(start_date, end_date))


@router.get("/categories", response_model=CategorySpendingResponse)
def category_spending(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CategorySpendingResponse:
    return get_category_spending(db, current_user, _date_range(start_date, end_date))


@router.get("/monthly", response_model=MonthlyAnalyticsResponse)
def monthly_analytics(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonthlyAnalyticsResponse:
    return get_monthly_analytics(db, current_user, _date_range(start_date, end_date))


@router.get("/merchants", response_model=MerchantSpendingResponse)
def top_merchants(
    start_date: date,
    end_date: date,
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MerchantSpendingResponse:
    return get_top_merchants(
        db,
        current_user,
        _date_range(start_date, end_date),
        limit,
    )


@router.get("/compare", response_model=PeriodComparisonResponse)
def period_comparison(
    period_a_start: date,
    period_a_end: date,
    period_b_start: date,
    period_b_end: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PeriodComparisonResponse:
    return compare_periods(
        db=db,
        current_user=current_user,
        period_a=_date_range(period_a_start, period_a_end),
        period_b=_date_range(period_b_start, period_b_end),
    )

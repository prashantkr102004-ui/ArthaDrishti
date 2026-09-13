from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.goal import FinancialGoal
from app.models.user import User
from app.schemas.goal import (
    AffordabilityRequest,
    AffordabilityResponse,
    GoalCreate,
    GoalFeasibility,
    GoalListResponse,
    GoalRead,
    GoalUpdate,
)
from app.services.analytics import DateRange, get_monthly_analytics

MONEY_QUANT = Decimal("0.0001")
ZERO = Decimal("0.0000")


def create_goal(db: Session, current_user: User, payload: GoalCreate) -> GoalRead:
    goal = FinancialGoal(
        user_id=current_user.id,
        name=payload.name.strip(),
        target_amount=payload.target_amount,
        target_date=payload.target_date,
        current_saved_amount=payload.current_saved_amount,
        status="active",
    )
    db.add(goal)
    _commit(db)
    db.refresh(goal)
    return goal_to_read(db, current_user, goal)


def list_goals(db: Session, current_user: User, today: date | None = None) -> GoalListResponse:
    goals = list(
        db.scalars(
            select(FinancialGoal)
            .where(FinancialGoal.user_id == current_user.id)
            .order_by(FinancialGoal.target_date.asc(), FinancialGoal.id.asc())
        )
    )
    return GoalListResponse(items=[goal_to_read(db, current_user, goal, today) for goal in goals])


def get_user_goal(db: Session, current_user: User, goal_id: UUID) -> FinancialGoal:
    goal = db.scalar(
        select(FinancialGoal).where(
            FinancialGoal.id == goal_id,
            FinancialGoal.user_id == current_user.id,
        )
    )
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


def update_goal(
    db: Session,
    current_user: User,
    goal_id: UUID,
    payload: GoalUpdate,
) -> GoalRead:
    goal = get_user_goal(db, current_user, goal_id)
    if payload.name is not None:
        goal.name = payload.name.strip()
    if payload.target_amount is not None:
        goal.target_amount = payload.target_amount
    if payload.target_date is not None:
        goal.target_date = payload.target_date
    if payload.current_saved_amount is not None:
        goal.current_saved_amount = payload.current_saved_amount
    if payload.status is not None:
        goal.status = payload.status.value
    _commit(db)
    db.refresh(goal)
    return goal_to_read(db, current_user, goal)


def delete_goal(db: Session, current_user: User, goal_id: UUID) -> None:
    goal = get_user_goal(db, current_user, goal_id)
    db.delete(goal)
    _commit(db)


def goal_to_read(
    db: Session,
    current_user: User,
    goal: FinancialGoal,
    today: date | None = None,
) -> GoalRead:
    run_date = today or date.today()
    historical = historical_monthly_savings(db, current_user, run_date)
    remaining = _money(max(goal.target_amount - goal.current_saved_amount, ZERO))
    months = months_remaining(run_date, goal.target_date)
    required = _required_monthly_saving(remaining, months)
    feasibility = _feasibility(remaining, required, historical, months, goal.status)
    gap = None if required is None or historical is None else _money(historical - required)
    return GoalRead(
        id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        target_date=goal.target_date,
        current_saved_amount=goal.current_saved_amount,
        status=goal.status,
        remaining_amount=remaining,
        months_remaining=months,
        required_monthly_saving=required,
        historical_monthly_savings=historical,
        monthly_gap_or_surplus=gap,
        progress_percentage=_progress_percentage(goal.current_saved_amount, goal.target_amount),
        feasibility=feasibility,
        recommendation=_goal_recommendation(remaining, required, historical, gap, months, feasibility),
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


def check_affordability(
    db: Session,
    current_user: User,
    payload: AffordabilityRequest,
    today: date | None = None,
) -> AffordabilityResponse:
    run_date = today or date.today()
    remaining = _money(max(payload.target_amount - payload.current_saved_amount, ZERO))
    months = months_remaining(run_date, payload.target_date)
    required = _required_monthly_saving(remaining, months)
    historical = historical_monthly_savings(db, current_user, run_date)
    gap = None if required is None or historical is None else _money(historical - required)
    feasibility = _feasibility(remaining, required, historical, months, "active")
    return AffordabilityResponse(
        name=payload.name.strip(),
        target_amount=payload.target_amount,
        target_date=payload.target_date,
        current_saved_amount=payload.current_saved_amount,
        remaining_amount=remaining,
        months_remaining=months,
        required_monthly_saving=required,
        historical_monthly_savings=historical,
        gap_or_surplus=gap,
        feasibility=feasibility,
        note="This estimate is based on historical savings, not a guarantee.",
    )


def historical_monthly_savings(
    db: Session,
    current_user: User,
    today: date | None = None,
    months: int = 3,
) -> Decimal | None:
    run_date = today or date.today()
    first_month = _month_shift(date(run_date.year, run_date.month, 1), -months)
    last_month_end = date(run_date.year, run_date.month, 1)
    response = get_monthly_analytics(
        db,
        current_user,
        DateRange(start_date=first_month, end_date=last_month_end),
    )
    items = [item for item in response.items if item.month < f"{run_date.year:04d}-{run_date.month:02d}"]
    if len(items) < 3:
        return None
    return _money(sum((item.savings for item in items), ZERO) / Decimal(len(items)))


def months_remaining(today: date, target_date: date) -> int:
    if target_date <= today:
        return 0
    months = (target_date.year - today.year) * 12 + target_date.month - today.month
    return max(months, 1)


def _required_monthly_saving(remaining: Decimal, months: int) -> Decimal | None:
    if remaining <= ZERO:
        return ZERO
    if months <= 0:
        return None
    return _money(remaining / Decimal(months))


def _feasibility(
    remaining: Decimal,
    required: Decimal | None,
    historical: Decimal | None,
    months: int,
    status_value: str,
) -> GoalFeasibility:
    if remaining <= ZERO or status_value == "completed":
        return GoalFeasibility.completed
    if months <= 0 or required is None:
        return GoalFeasibility.currently_unrealistic
    if historical is None:
        return GoalFeasibility.needs_adjustment
    if historical >= required:
        return GoalFeasibility.likely_on_track
    if historical >= required * Decimal("0.75"):
        return GoalFeasibility.needs_adjustment
    return GoalFeasibility.currently_unrealistic


def _month_shift(month_start: date, months: int) -> date:
    month_index = month_start.month - 1 + months
    year = month_start.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _progress_percentage(current_saved: Decimal, target: Decimal) -> Decimal:
    if target <= ZERO:
        return ZERO
    return _money(min((current_saved / target) * Decimal("100"), Decimal("100")))


def _goal_recommendation(
    remaining: Decimal,
    required: Decimal | None,
    historical: Decimal | None,
    gap: Decimal | None,
    months: int,
    feasibility: GoalFeasibility,
) -> str:
    if feasibility == GoalFeasibility.completed:
        return "This goal is already funded based on the saved amount entered."
    if months <= 0 or required is None:
        return "The target date has passed or is today. Update the date or saved amount to make this goal realistic."
    if historical is None:
        return (
            f"Save {required} per month to reach this goal. Add at least 3 completed months "
            "of transaction history for an affordability comparison."
        )
    if gap is not None and gap >= ZERO:
        return (
            f"Save {required} per month. Your recent average monthly savings are {historical}, "
            f"which is {gap} above the required pace."
        )
    shortfall = _money(abs(gap or ZERO))
    return (
        f"Save {required} per month. Your recent average monthly savings are {historical}, "
        f"so you are about {shortfall} per month short of the current target pace."
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Goal operation failed.",
        ) from exc

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.budget import Budget
from app.models.category import Category
from app.models.user import User
from app.schemas.budget import (
    BudgetCreate,
    BudgetListResponse,
    BudgetProgressItem,
    BudgetProgressResponse,
    BudgetStatus,
    BudgetUpdate,
)
from app.services.analytics import DateRange, get_category_spending

ZERO = Decimal("0.0000")
ONE_HUNDRED = Decimal("100")


def create_budget(db: Session, current_user: User, payload: BudgetCreate) -> Budget:
    _validate_category(db, payload.category_id)
    budget = Budget(
        user_id=current_user.id,
        category_id=payload.category_id,
        amount=payload.amount,
        period=payload.period.value,
        start_date=payload.start_date,
    )
    db.add(budget)
    _commit(db)
    db.refresh(budget)
    return budget


def list_budgets(db: Session, current_user: User) -> BudgetListResponse:
    return BudgetListResponse(items=_list_budget_rows(db, current_user))


def _list_budget_rows(db: Session, current_user: User) -> list[Budget]:
    items = list(
        db.scalars(
            select(Budget)
            .options(joinedload(Budget.category))
            .where(Budget.user_id == current_user.id)
            .order_by(Budget.created_at.desc(), Budget.id.desc())
        )
    )
    return items


def get_user_budget(db: Session, current_user: User, budget_id: UUID) -> Budget:
    budget = db.scalar(
        select(Budget)
        .options(joinedload(Budget.category))
        .where(Budget.id == budget_id, Budget.user_id == current_user.id)
    )
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget


def update_budget(
    db: Session,
    current_user: User,
    budget_id: UUID,
    payload: BudgetUpdate,
) -> Budget:
    budget = get_user_budget(db, current_user, budget_id)
    if payload.category_id is not None:
        _validate_category(db, payload.category_id)
        budget.category_id = payload.category_id
    if payload.amount is not None:
        budget.amount = payload.amount
    if payload.start_date is not None:
        budget.start_date = payload.start_date
    _commit(db)
    db.refresh(budget)
    return budget


def delete_budget(db: Session, current_user: User, budget_id: UUID) -> None:
    budget = get_user_budget(db, current_user, budget_id)
    db.delete(budget)
    _commit(db)


def get_budget_progress(
    db: Session,
    current_user: User,
    start_date: date,
    end_date: date,
) -> BudgetProgressResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date must be on or before end_date.",
        )
    budgets = _list_budget_rows(db, current_user)
    category_spending = get_category_spending(
        db,
        current_user,
        DateRange(start_date=start_date, end_date=end_date),
    )
    spending_by_category = {
        item.category_id: item.amount
        for item in category_spending.items
    }
    total_spending = sum((item.amount for item in category_spending.items), ZERO)
    items = []
    for budget in budgets:
        spent = total_spending if budget.category_id is None else spending_by_category.get(budget.category_id, ZERO)
        percentage = _percentage(spent, budget.amount)
        items.append(
            BudgetProgressItem(
                budget_id=budget.id,
                category_id=budget.category_id,
                category_name=budget.category.name if budget.category else "Overall spending",
                budget_amount=budget.amount,
                spent_amount=spent,
                remaining_amount=budget.amount - spent,
                percentage_used=percentage,
                status=_budget_status(percentage),
            )
        )
    return BudgetProgressResponse(start_date=start_date, end_date=end_date, items=items)


def _validate_category(db: Session, category_id: UUID | None) -> None:
    if category_id is None:
        return
    exists = db.scalar(select(Category.id).where(Category.id == category_id))
    if exists is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Category not found")


def _percentage(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == ZERO:
        return ZERO
    return ((numerator / denominator) * ONE_HUNDRED).quantize(Decimal("0.0001"))


def _budget_status(percentage: Decimal) -> BudgetStatus:
    if percentage > ONE_HUNDRED:
        return BudgetStatus.exceeded
    if percentage >= Decimal("80"):
        return BudgetStatus.near_limit
    return BudgetStatus.on_track


def _commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Budget operation failed.",
        ) from exc

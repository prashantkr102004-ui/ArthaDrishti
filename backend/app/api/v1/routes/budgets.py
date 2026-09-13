from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetListResponse, BudgetProgressResponse, BudgetRead, BudgetUpdate
from app.services.budgets import create_budget, delete_budget, get_budget_progress, list_budgets, update_budget

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def create_user_budget(
    payload: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BudgetRead:
    return create_budget(db, current_user, payload)


@router.get("", response_model=BudgetListResponse)
def list_user_budgets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BudgetListResponse:
    return list_budgets(db, current_user)


@router.get("/progress", response_model=BudgetProgressResponse)
def budget_progress(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BudgetProgressResponse:
    return get_budget_progress(db, current_user, start_date, end_date)


@router.patch("/{budget_id}", response_model=BudgetRead)
def update_user_budget(
    budget_id: UUID,
    payload: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BudgetRead:
    return update_budget(db, current_user, budget_id, payload)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_budget(
    budget_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    delete_budget(db, current_user, budget_id)

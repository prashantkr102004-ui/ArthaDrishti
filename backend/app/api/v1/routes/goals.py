from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.goal import (
    AffordabilityRequest,
    AffordabilityResponse,
    GoalCreate,
    GoalListResponse,
    GoalRead,
    GoalUpdate,
)
from app.services.goals import check_affordability, create_goal, delete_goal, list_goals, update_goal

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
def create_user_goal(
    payload: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalRead:
    return create_goal(db, current_user, payload)


@router.get("", response_model=GoalListResponse)
def list_user_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalListResponse:
    return list_goals(db, current_user)


@router.patch("/{goal_id}", response_model=GoalRead)
def update_user_goal(
    goal_id: UUID,
    payload: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalRead:
    return update_goal(db, current_user, goal_id, payload)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    delete_goal(db, current_user, goal_id)


@router.post("/affordability", response_model=AffordabilityResponse)
def goal_affordability(
    payload: AffordabilityRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AffordabilityResponse:
    return check_affordability(db, current_user, payload, today=date.today())

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GoalStatus(StrEnum):
    active = "active"
    completed = "completed"
    paused = "paused"


class GoalFeasibility(StrEnum):
    likely_on_track = "likely_on_track"
    needs_adjustment = "needs_adjustment"
    currently_unrealistic = "currently_unrealistic"
    completed = "completed"


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=0)
    target_date: date
    current_saved_amount: Decimal = Field(default=Decimal("0.0000"), ge=0)


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: Decimal | None = Field(default=None, gt=0)
    target_date: date | None = None
    current_saved_amount: Decimal | None = Field(default=None, ge=0)
    status: GoalStatus | None = None


class GoalRead(BaseModel):
    id: UUID
    name: str
    target_amount: Decimal
    target_date: date
    current_saved_amount: Decimal
    status: GoalStatus
    remaining_amount: Decimal
    months_remaining: int
    required_monthly_saving: Decimal | None
    historical_monthly_savings: Decimal | None
    monthly_gap_or_surplus: Decimal | None
    progress_percentage: Decimal
    feasibility: GoalFeasibility
    recommendation: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalListResponse(BaseModel):
    items: list[GoalRead]


class AffordabilityRequest(BaseModel):
    name: str = Field(default="Planned purchase", min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=0)
    target_date: date
    current_saved_amount: Decimal = Field(default=Decimal("0.0000"), ge=0)


class AffordabilityResponse(BaseModel):
    name: str
    target_amount: Decimal
    target_date: date
    current_saved_amount: Decimal
    remaining_amount: Decimal
    months_remaining: int
    required_monthly_saving: Decimal | None
    historical_monthly_savings: Decimal | None
    gap_or_surplus: Decimal | None
    feasibility: GoalFeasibility
    note: str

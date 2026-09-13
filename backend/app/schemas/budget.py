from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BudgetPeriod(StrEnum):
    monthly = "monthly"


class BudgetStatus(StrEnum):
    on_track = "on_track"
    near_limit = "near_limit"
    exceeded = "exceeded"


class BudgetCreate(BaseModel):
    category_id: UUID | None = None
    amount: Decimal = Field(gt=0)
    period: BudgetPeriod = BudgetPeriod.monthly
    start_date: date


class BudgetUpdate(BaseModel):
    category_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    start_date: date | None = None


class BudgetRead(BaseModel):
    id: UUID
    category_id: UUID | None
    category_name: str | None = None
    amount: Decimal
    period: BudgetPeriod
    start_date: date
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetListResponse(BaseModel):
    items: list[BudgetRead]


class BudgetProgressItem(BaseModel):
    budget_id: UUID
    category_id: UUID | None
    category_name: str
    budget_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    percentage_used: Decimal
    status: BudgetStatus


class BudgetProgressResponse(BaseModel):
    start_date: date
    end_date: date
    items: list[BudgetProgressItem]

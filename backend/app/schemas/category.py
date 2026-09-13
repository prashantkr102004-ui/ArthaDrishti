from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategoryRead(BaseModel):
    id: UUID
    name: str
    slug: str
    parent_id: UUID | None
    is_system: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryListResponse(BaseModel):
    items: list[CategoryRead]


class TransactionCategoryUpdate(BaseModel):
    category_id: UUID
    apply_to_merchant: bool = True

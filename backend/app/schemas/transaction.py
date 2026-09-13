from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.parsing import TransactionDirection


class TransactionRead(BaseModel):
    id: UUID
    document_id: UUID
    transaction_date: date
    value_date: date | None
    raw_description: str
    normalized_description: str
    canonical_merchant: str | None
    category_id: UUID | None
    category_name: str | None = None
    categorization_confidence: Decimal | None
    categorization_source: str | None
    amount: Decimal
    direction: TransactionDirection
    balance: Decimal | None
    currency: str
    source_page: int | None
    source_row: int | None
    extraction_confidence: Decimal | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    items: list[TransactionRead]
    total: int
    limit: int
    offset: int


class TransactionImportSummary(BaseModel):
    document_id: UUID
    parsed: int
    inserted: int
    duplicates: int
    failed: int

from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import DocumentProcessingStatus


class TransactionDirection(StrEnum):
    debit = "debit"
    credit = "credit"


class ParseResultStatus(StrEnum):
    success = "success"
    partial_success = "partial_success"
    failed = "failed"


class ParserIssue(BaseModel):
    code: str
    message: str
    source_page: int | None = None
    source_row: int | None = None


class StatementMetadata(BaseModel):
    bank_name: str | None = None
    masked_account_number: str | None = None
    statement_start_date: date | None = None
    statement_end_date: date | None = None
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    currency: str = "INR"


class ExtractedTransaction(BaseModel):
    transaction_date: date
    value_date: date | None = None
    raw_description: str
    amount: Decimal
    direction: TransactionDirection
    balance: Decimal | None = None
    raw_debit: str | None = None
    raw_credit: str | None = None
    source_page: int | None = None
    source_row: int | None = None
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class ParseResult(BaseModel):
    parser_name: str
    parser_version: str
    document_id: UUID
    status: ParseResultStatus
    metadata: StatementMetadata = Field(default_factory=StatementMetadata)
    transactions: list[ExtractedTransaction] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[ParserIssue] = Field(default_factory=list)

    @property
    def transaction_count(self) -> int:
        return len(self.transactions)


class StoredTransactionPreview(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)


class DocumentParseResponse(BaseModel):
    document_id: UUID
    status: DocumentProcessingStatus
    parser_name: str | None = None
    parser_version: str | None = None
    result_status: ParseResultStatus
    transaction_count: int
    warning_count: int
    error_count: int
    rows_parsed: int = 0
    inserted_count: int = 0
    duplicate_count: int = 0
    failed_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[ParserIssue] = Field(default_factory=list)
    preview_transactions: list[StoredTransactionPreview] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

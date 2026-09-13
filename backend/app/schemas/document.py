from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentType(StrEnum):
    bank_statement = "bank_statement"
    credit_card_statement = "credit_card_statement"


class DocumentProcessingStatus(StrEnum):
    ready_for_processing = "ready_for_processing"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class DocumentIndexingStatus(StrEnum):
    not_indexed = "not_indexed"
    indexing = "indexing"
    indexed = "indexed"
    indexing_failed = "indexing_failed"


class DocumentRead(BaseModel):
    id: UUID
    original_filename: str
    document_type: DocumentType
    mime_type: str
    file_size_bytes: int
    processing_status: DocumentProcessingStatus
    processing_error: str | None
    indexing_status: DocumentIndexingStatus
    indexing_error: str | None
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    items: list[DocumentRead]
    total: int
    limit: int
    offset: int

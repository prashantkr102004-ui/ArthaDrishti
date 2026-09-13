from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.document import DocumentIndexingStatus


class DocumentIndexResponse(BaseModel):
    document_id: UUID
    status: DocumentIndexingStatus
    chunks_created: int
    embedding_model: str
    error: str | None = None


class DocumentSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    document_id: UUID | None = None
    top_k: int = Field(default=5, ge=1, le=10)


class DocumentSearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_name: str
    page_number: int | None
    chunk_index: int
    text: str
    score: float


class DocumentSearchResponse(BaseModel):
    query: str
    results: list[DocumentSearchResult]
    result_count: int

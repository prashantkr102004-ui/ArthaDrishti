import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.parsing.exceptions import ParsingError
from app.parsing.pdf import extract_pdf_text
from app.rag.chunking import chunk_pdf_text
from app.rag.embeddings import EmbeddingProvider, EmbeddingProviderError, get_embedding_provider
from app.schemas.document import DocumentIndexingStatus
from app.schemas.document_search import DocumentIndexResponse
from app.services.document_storage import DocumentStorageService
from app.services.documents import get_user_document

logger = logging.getLogger(__name__)


def index_user_document(
    *,
    db: Session,
    current_user: User,
    document_id: UUID,
    storage: DocumentStorageService,
    embedding_provider: EmbeddingProvider | None = None,
) -> DocumentIndexResponse:
    document = get_user_document(db, current_user, document_id)
    provider = embedding_provider or get_embedding_provider()
    _set_indexing_state(db, document, DocumentIndexingStatus.indexing.value, None)

    try:
        file_path = storage.path_for_read(document.storage_key)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file is missing from private storage.",
            )

        pdf_text = extract_pdf_text(file_path)
        chunks = chunk_pdf_text(pdf_text)
        if not chunks:
            raise ParsingError("no_extractable_text", "No extractable text was found.")

        embeddings = provider.embed_many([chunk.text for chunk in chunks])
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            db.add(
                DocumentChunk(
                    user_id=current_user.id,
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    text=chunk.text,
                    embedding=embedding,
                    embedding_model=provider.model,
                    character_count=chunk.character_count,
                )
            )
        document.indexing_status = DocumentIndexingStatus.indexed.value
        document.indexing_error = None
        db.commit()
        logger.info(
            "document_indexed",
            extra={
                "document_id": str(document.id),
                "user_id": str(current_user.id),
                "chunk_count": len(chunks),
                "embedding_model": provider.model,
            },
        )
        return DocumentIndexResponse(
            document_id=document.id,
            status=DocumentIndexingStatus.indexed,
            chunks_created=len(chunks),
            embedding_model=provider.model,
            error=None,
        )
    except HTTPException as exc:
        _mark_failed(db, document, str(exc.detail))
        raise
    except ParsingError as exc:
        _mark_failed(db, document, exc.detail.message)
        return DocumentIndexResponse(
            document_id=document.id,
            status=DocumentIndexingStatus.indexing_failed,
            chunks_created=0,
            embedding_model=provider.model,
            error=exc.detail.message,
        )
    except SQLAlchemyError as exc:
        db.rollback()
        _mark_failed(db, document, "Document indexing failed.")
        logger.warning("document_indexing_failed", extra={"document_id": str(document.id)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document indexing failed.",
        ) from exc
    except (EmbeddingProviderError, OSError, ValueError) as exc:
        _mark_failed(db, document, "Document indexing failed.")
        logger.warning("document_indexing_failed", extra={"document_id": str(document.id)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document indexing failed.",
        ) from exc


def _set_indexing_state(db: Session, document: Document, status_value: str, error: str | None) -> None:
    document.indexing_status = status_value
    document.indexing_error = error
    db.commit()
    db.refresh(document)


def _mark_failed(db: Session, document: Document, message: str) -> None:
    document.indexing_status = DocumentIndexingStatus.indexing_failed.value
    document.indexing_error = message
    db.commit()

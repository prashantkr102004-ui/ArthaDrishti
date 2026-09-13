import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentProcessingStatus, DocumentType
from app.services.document_storage import DocumentStorageService

logger = logging.getLogger(__name__)

PDF_SIGNATURE = b"%PDF-"
STORAGE_BACKEND_LOCAL = "local"


class UploadValidationResult:
    def __init__(
        self,
        content: bytes,
        file_hash: str,
        safe_filename: str,
        mime_type: str,
    ) -> None:
        self.content = content
        self.file_hash = file_hash
        self.safe_filename = safe_filename
        self.mime_type = mime_type

    @property
    def file_size_bytes(self) -> int:
        return len(self.content)


def get_document_storage() -> DocumentStorageService:
    return DocumentStorageService(settings.resolved_document_storage_path)


def sanitize_original_filename(filename: str | None) -> str:
    if not filename:
        return "uploaded.pdf"
    name = Path(filename).name.strip()
    return name or "uploaded.pdf"


async def validate_upload(file: UploadFile) -> UploadValidationResult:
    original_filename = sanitize_original_filename(file.filename)
    if Path(original_filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported",
        )

    content_type = file.content_type or ""
    if content_type not in settings.allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported",
        )

    content = await file.read(settings.max_upload_size_bytes + 1)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_size_mb} MB upload limit",
        )
    if not content.startswith(PDF_SIGNATURE):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Uploaded file is not a valid PDF",
        )

    return UploadValidationResult(
        content=content,
        file_hash=hashlib.sha256(content).hexdigest(),
        safe_filename=original_filename,
        mime_type=content_type,
    )


def generate_storage_key(user_id: UUID) -> str:
    return f"{user_id}/{uuid4()}.pdf"


def get_user_document(db: Session, current_user: User, document_id: UUID) -> Document:
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


async def create_document_from_upload(
    db: Session,
    current_user: User,
    file: UploadFile,
    document_type: DocumentType,
    storage: DocumentStorageService,
) -> Document:
    validation = await validate_upload(file)

    existing_document = db.scalar(
        select(Document).where(
            Document.user_id == current_user.id,
            Document.sha256_hash == validation.file_hash,
        )
    )
    if existing_document is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This exact document has already been uploaded",
        )

    storage_key = generate_storage_key(current_user.id)
    saved = False

    try:
        storage.save(storage_key, validation.content)
        saved = True

        timestamp = datetime.now(UTC)
        document = Document(
            user_id=current_user.id,
            document_type=document_type.value,
            original_filename=validation.safe_filename,
            storage_backend=STORAGE_BACKEND_LOCAL,
            storage_key=storage_key,
            mime_type=validation.mime_type,
            file_size_bytes=validation.file_size_bytes,
            sha256_hash=validation.file_hash,
            processing_status=DocumentProcessingStatus.ready_for_processing.value,
            uploaded_at=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        logger.info("Document upload stored", extra={"document_id": str(document.id)})
        return document
    except SQLAlchemyError as exc:
        db.rollback()
        if saved:
            storage.delete(storage_key)
        logger.warning("Document metadata insert failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload could not be saved",
        ) from exc
    except OSError as exc:
        db.rollback()
        logger.warning("Document file storage failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document file could not be stored",
        ) from exc


def list_user_documents(
    db: Session,
    current_user: User,
    limit: int,
    offset: int,
    document_type: DocumentType | None = None,
    processing_status: DocumentProcessingStatus | None = None,
) -> tuple[list[Document], int]:
    filters = [Document.user_id == current_user.id]
    if document_type is not None:
        filters.append(Document.document_type == document_type.value)
    if processing_status is not None:
        filters.append(Document.processing_status == processing_status.value)

    total = db.scalar(select(func.count()).select_from(Document).where(*filters)) or 0
    documents = list(
        db.scalars(
            select(Document)
            .where(*filters)
            .order_by(Document.uploaded_at.desc(), Document.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return documents, total


def delete_user_document(
    db: Session,
    current_user: User,
    document_id: UUID,
    storage: DocumentStorageService,
) -> None:
    document = get_user_document(db, current_user, document_id)
    from app.services.transactions import document_has_transactions

    if document_has_transactions(db, document_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document cannot be deleted after transactions have been imported",
        )

    storage_key = document.storage_key

    try:
        db.delete(document)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("Document metadata delete failed", extra={"document_id": str(document_id)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document could not be deleted",
        ) from exc

    try:
        storage.delete(storage_key)
        logger.info("Document deleted", extra={"document_id": str(document_id)})
    except (OSError, ValueError) as exc:
        logger.warning("Document metadata deleted but file cleanup failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document metadata was deleted but file cleanup failed",
        ) from exc

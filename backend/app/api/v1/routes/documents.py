from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import (
    DocumentListResponse,
    DocumentProcessingStatus,
    DocumentRead,
    DocumentType,
)
from app.schemas.document_search import DocumentIndexResponse
from app.schemas.parsing import DocumentParseResponse
from app.rag.indexing import index_user_document
from app.services.document_storage import DocumentStorageService
from app.services.document_parsing import parse_user_document
from app.services.documents import (
    create_document_from_upload,
    delete_user_document,
    get_document_storage,
    get_user_document,
    list_user_documents,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: DocumentStorageService = Depends(get_document_storage),
) -> DocumentRead:
    return await create_document_from_upload(
        db=db,
        current_user=current_user,
        file=file,
        document_type=document_type,
        storage=storage,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    document_type: DocumentType | None = None,
    processing_status: DocumentProcessingStatus | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> DocumentListResponse:
    documents, total = list_user_documents(
        db=db,
        current_user=current_user,
        document_type=document_type,
        processing_status=processing_status,
        limit=limit,
        offset=offset,
    )
    return DocumentListResponse(
        items=documents,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentRead:
    return get_user_document(db, current_user, document_id)


@router.post("/{document_id}/parse", response_model=DocumentParseResponse)
def parse_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: DocumentStorageService = Depends(get_document_storage),
) -> DocumentParseResponse:
    return parse_user_document(
        db=db,
        current_user=current_user,
        document_id=document_id,
        storage=storage,
    )


@router.post("/{document_id}/index", response_model=DocumentIndexResponse)
def index_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: DocumentStorageService = Depends(get_document_storage),
) -> DocumentIndexResponse:
    return index_user_document(
        db=db,
        current_user=current_user,
        document_id=document_id,
        storage=storage,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: DocumentStorageService = Depends(get_document_storage),
) -> None:
    delete_user_document(
        db=db,
        current_user=current_user,
        document_id=document_id,
        storage=storage,
    )

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.rag.retrieval import search_user_document_chunks
from app.schemas.document_search import DocumentSearchRequest, DocumentSearchResponse

router = APIRouter(prefix="/document-search", tags=["document-search"])


@router.post("", response_model=DocumentSearchResponse)
def search_documents(
    request: DocumentSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentSearchResponse:
    results = search_user_document_chunks(
        db=db,
        current_user=current_user,
        query=request.query,
        document_id=request.document_id,
        top_k=request.top_k,
    )
    return DocumentSearchResponse(
        query=request.query,
        results=results,
        result_count=len(results),
    )

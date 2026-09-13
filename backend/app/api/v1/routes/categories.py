from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.category import CategoryListResponse
from app.services.categorization import list_categories

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=CategoryListResponse)
def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CategoryListResponse:
    _ = current_user
    return CategoryListResponse(items=list_categories(db))

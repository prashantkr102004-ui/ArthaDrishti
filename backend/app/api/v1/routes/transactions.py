from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.category import TransactionCategoryUpdate
from app.schemas.parsing import TransactionDirection
from app.schemas.transaction import TransactionListResponse, TransactionRead
from app.services.categorization import recategorize_transaction
from app.services.transactions import get_user_transaction, list_user_transactions

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: date | None = None,
    end_date: date | None = None,
    direction: TransactionDirection | None = None,
    document_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TransactionListResponse:
    transactions, total = list_user_transactions(
        db=db,
        current_user=current_user,
        start_date=start_date,
        end_date=end_date,
        direction=direction,
        document_id=document_id,
        limit=limit,
        offset=offset,
    )
    return TransactionListResponse(
        items=transactions,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionRead:
    return get_user_transaction(db, current_user, transaction_id)


@router.patch("/{transaction_id}/category", response_model=TransactionRead)
def update_transaction_category(
    transaction_id: UUID,
    payload: TransactionCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionRead:
    return recategorize_transaction(
        db=db,
        current_user=current_user,
        transaction_id=transaction_id,
        category_id=payload.category_id,
        apply_to_merchant=payload.apply_to_merchant,
    )

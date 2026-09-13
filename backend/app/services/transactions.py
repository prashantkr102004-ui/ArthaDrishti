import hashlib
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.parsing import ExtractedTransaction, TransactionDirection
from app.schemas.transaction import TransactionImportSummary

MONEY_QUANT = Decimal("0.0001")
CONFIDENCE_QUANT = Decimal("0.0001")
SUPPORTED_CURRENCIES = {"INR"}


@dataclass(frozen=True)
class CanonicalTransactionData:
    document_id: UUID
    user_id: UUID
    transaction_date: date
    value_date: date | None
    raw_description: str
    normalized_description: str
    canonical_merchant: str | None
    merchant_key: str | None
    category_id: UUID | None
    categorization_confidence: Decimal | None
    categorization_source: str | None
    amount: Decimal
    direction: TransactionDirection
    balance: Decimal | None
    currency: str
    source_page: int | None
    source_row: int | None
    extraction_confidence: Decimal | None
    dedupe_fingerprint: str


def normalize_description(description: str) -> str:
    return re.sub(r"\s+", " ", description).strip()


def normalize_currency(currency: str | None) -> str:
    normalized = (currency or "INR").strip().upper()
    if normalized not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported currency: {currency}")
    return normalized


def normalize_money(value: Decimal) -> Decimal:
    amount = value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    if amount <= 0:
        raise ValueError("Transaction amount must be greater than zero.")
    return amount


def normalize_optional_money(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def normalize_confidence(value: float | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(CONFIDENCE_QUANT, rounding=ROUND_HALF_UP)


def build_transaction_fingerprint(
    *,
    user_id: UUID,
    transaction_date: date,
    value_date: date | None,
    amount: Decimal,
    direction: TransactionDirection,
    normalized_description: str,
    balance: Decimal | None,
    currency: str,
) -> str:
    parts = [
        "v1",
        f"user={user_id}",
        "account=none",
        f"transaction_date={transaction_date.isoformat()}",
        f"value_date={value_date.isoformat() if value_date else ''}",
        f"amount={amount}",
        f"direction={direction.value}",
        f"currency={currency}",
        f"description={normalized_description.casefold()}",
        f"balance={balance if balance is not None else ''}",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def canonicalize_extracted_transaction(
    *,
    document: Document,
    extracted: ExtractedTransaction,
    currency: str | None,
) -> CanonicalTransactionData:
    raw_description = extracted.raw_description.strip()
    normalized_description = normalize_description(raw_description)
    if not raw_description or not normalized_description:
        raise ValueError("Transaction description is required.")

    amount = normalize_money(extracted.amount)
    balance = normalize_optional_money(extracted.balance)
    normalized_currency = normalize_currency(currency)
    confidence = normalize_confidence(extracted.extraction_confidence)

    fingerprint = build_transaction_fingerprint(
        user_id=document.user_id,
        transaction_date=extracted.transaction_date,
        value_date=extracted.value_date,
        amount=amount,
        direction=extracted.direction,
        normalized_description=normalized_description,
        balance=balance,
        currency=normalized_currency,
    )

    return CanonicalTransactionData(
        document_id=document.id,
        user_id=document.user_id,
        transaction_date=extracted.transaction_date,
        value_date=extracted.value_date,
        raw_description=raw_description,
        normalized_description=normalized_description,
        canonical_merchant=None,
        merchant_key=None,
        category_id=None,
        categorization_confidence=None,
        categorization_source=None,
        amount=amount,
        direction=extracted.direction,
        balance=balance,
        currency=normalized_currency,
        source_page=extracted.source_page,
        source_row=extracted.source_row,
        extraction_confidence=confidence,
        dedupe_fingerprint=fingerprint,
    )


def import_extracted_transactions(
    db: Session,
    document: Document,
    extracted_transactions: list[ExtractedTransaction],
    currency: str | None,
    failed_rows: int = 0,
) -> TransactionImportSummary:
    canonical_rows: list[CanonicalTransactionData] = []
    normalization_failures = 0

    for extracted in extracted_transactions:
        try:
            canonical_rows.append(
                canonicalize_extracted_transaction(
                    document=document,
                    extracted=extracted,
                    currency=currency,
                )
            )
        except ValueError:
            normalization_failures += 1

    fingerprints = [row.dedupe_fingerprint for row in canonical_rows]
    existing_fingerprints = set(
        db.scalars(
            select(Transaction.dedupe_fingerprint).where(
                Transaction.user_id == document.user_id,
                Transaction.dedupe_fingerprint.in_(fingerprints),
            )
        )
    ) if fingerprints else set()

    inserted = 0
    duplicates = 0
    for row in canonical_rows:
        if row.dedupe_fingerprint in existing_fingerprints:
            duplicates += 1
            continue

        from app.services.categorization import categorize_description

        categorization = categorize_description(
            db=db,
            user_id=row.user_id,
            description=row.normalized_description,
        )

        db.add(
            Transaction(
                user_id=row.user_id,
                document_id=row.document_id,
                transaction_date=row.transaction_date,
                value_date=row.value_date,
                raw_description=row.raw_description,
                normalized_description=row.normalized_description,
                canonical_merchant=categorization.canonical_merchant,
                merchant_key=categorization.merchant_key,
                category_id=categorization.category_id,
                categorization_confidence=categorization.confidence,
                categorization_source=categorization.source,
                amount=row.amount,
                direction=row.direction.value,
                balance=row.balance,
                currency=row.currency,
                source_page=row.source_page,
                source_row=row.source_row,
                extraction_confidence=row.extraction_confidence,
                dedupe_fingerprint=row.dedupe_fingerprint,
            )
        )
        existing_fingerprints.add(row.dedupe_fingerprint)
        inserted += 1

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transaction import conflicted with existing records.",
        ) from None

    return TransactionImportSummary(
        document_id=document.id,
        parsed=len(extracted_transactions),
        inserted=inserted,
        duplicates=duplicates,
        failed=failed_rows + normalization_failures,
    )


def list_user_transactions(
    db: Session,
    current_user: User,
    limit: int,
    offset: int,
    start_date: date | None = None,
    end_date: date | None = None,
    direction: TransactionDirection | None = None,
    document_id: UUID | None = None,
) -> tuple[list[Transaction], int]:
    filters = [Transaction.user_id == current_user.id]
    if start_date is not None:
        filters.append(Transaction.transaction_date >= start_date)
    if end_date is not None:
        filters.append(Transaction.transaction_date <= end_date)
    if direction is not None:
        filters.append(Transaction.direction == direction.value)
    if document_id is not None:
        filters.append(Transaction.document_id == document_id)

    total = db.scalar(select(func.count()).select_from(Transaction).where(*filters)) or 0
    query: Select[tuple[Transaction]] = (
        select(Transaction)
        .where(*filters)
        .order_by(
            Transaction.transaction_date.desc(),
            Transaction.created_at.desc(),
            Transaction.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    transactions = list(db.scalars(query))
    return transactions, total


def get_user_transaction(
    db: Session,
    current_user: User,
    transaction_id: UUID,
) -> Transaction:
    transaction = db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return transaction


def document_has_transactions(db: Session, document_id: UUID) -> bool:
    return db.scalar(
        select(Transaction.id).where(Transaction.document_id == document_id).limit(1)
    ) is not None

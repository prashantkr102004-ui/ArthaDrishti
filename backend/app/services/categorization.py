import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.merchant import MerchantAlias, UserMerchantOverride
from app.models.transaction import Transaction
from app.models.user import User
from app.services.transactions import normalize_description

CONFIDENCE_QUANT = Decimal("0.0001")
OVERRIDE_CONFIDENCE = Decimal("1.0000")
EXACT_MERCHANT_CONFIDENCE = Decimal("1.0000")
REGEX_CONFIDENCE = Decimal("0.8500")
FALLBACK_CONFIDENCE = Decimal("0.4000")

PAYMENT_PREFIXES = {
    "UPI",
    "POS",
    "NEFT",
    "IMPS",
    "RTGS",
    "ACH",
    "VISA",
    "MASTERCARD",
    "CARD",
    "DEBIT",
    "CREDIT",
    "PAYMENT",
}

NOISE_TOKENS = {
    "PVT",
    "PRIVATE",
    "LTD",
    "LIMITED",
    "INDIA",
    "SERVICES",
    "SERVICE",
    "SELLER",
    "PAY",
    "TRIP",
    "BLR",
}

REGEX_RULES: tuple[tuple[re.Pattern[str], str, str | None], ...] = (
    (re.compile(r"\bSALARY\b|\bPAYROLL\b", re.IGNORECASE), "income", "Employer"),
    (re.compile(r"\bATM\b|\bCASH WITHDRAWAL\b", re.IGNORECASE), "atm", "ATM"),
    (re.compile(r"\bRENT\b", re.IGNORECASE), "rent", "Rent"),
    (re.compile(r"\bUTILITY\b|\bUTILITIES\b|\bELECTRICITY\b|\bBILL\b", re.IGNORECASE), "bills", "Utilities"),
    (re.compile(r"\bREFUND\b|\bREVERSAL\b", re.IGNORECASE), "other", "Refund"),
    (re.compile(r"\bTRANSFER\b|\bNEFT\b|\bIMPS\b|\bUPI\b", re.IGNORECASE), "transfers", None),
)


@dataclass(frozen=True)
class CategorizationResult:
    canonical_merchant: str | None
    merchant_key: str | None
    category_id: UUID
    category_name: str
    confidence: Decimal
    source: str


def normalize_merchant_key(value: str) -> str:
    cleaned = normalize_description(value)
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", cleaned).upper()
    tokens = [token for token in cleaned.split() if token]
    while tokens and tokens[0] in PAYMENT_PREFIXES:
        tokens.pop(0)
    tokens = [
        token
        for token in tokens
        if not re.fullmatch(r"[A-Z]*\d{5,}[A-Z0-9]*", token)
        and not re.fullmatch(r"(REF|UTR|TXN|RRN)[A-Z0-9]*", token)
    ]
    return " ".join(tokens)


def merchant_key_for_name(value: str | None) -> str | None:
    if value is None:
        return None
    key = normalize_merchant_key(value)
    return key or None


def display_merchant_from_key(merchant_key: str | None) -> str | None:
    if not merchant_key:
        return None
    meaningful = [
        token
        for token in merchant_key.split()
        if token not in NOISE_TOKENS and not token.isdigit()
    ]
    if not meaningful:
        return None
    return " ".join(token.capitalize() for token in meaningful[:3])


def build_alias_candidates(description: str) -> list[str]:
    key = normalize_merchant_key(description)
    if not key:
        return []

    tokens = key.split()
    candidates: list[str] = [key]
    max_window = min(4, len(tokens))
    for size in range(max_window, 0, -1):
        for start in range(0, len(tokens) - size + 1):
            candidate = " ".join(tokens[start : start + size])
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


def get_category_by_slug(db: Session, slug: str) -> Category:
    category = db.scalar(select(Category).where(Category.slug == slug))
    if category is None:
        raise RuntimeError(f"Required system category is missing: {slug}")
    return category


def list_categories(db: Session) -> list[Category]:
    return list(
        db.scalars(
            select(Category).order_by(
                Category.parent_id.is_not(None),
                Category.name.asc(),
            )
        )
    )


def get_category_or_404(db: Session, category_id: UUID) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


def categorize_description(
    db: Session,
    user_id: UUID,
    description: str,
) -> CategorizationResult:
    normalized_description = normalize_description(description)
    candidates = build_alias_candidates(normalized_description)

    alias = _find_best_alias(db, candidates)
    merchant_name = alias.merchant_name if alias else display_merchant_from_key(candidates[0] if candidates else None)
    merchant_key = merchant_key_for_name(merchant_name)

    if merchant_key:
        override = db.scalar(
            select(UserMerchantOverride).where(
                UserMerchantOverride.user_id == user_id,
                UserMerchantOverride.merchant_key == merchant_key,
            )
        )
        if override is not None:
            category = db.get(Category, override.category_id)
            if category is not None:
                return CategorizationResult(
                    canonical_merchant=override.merchant_name,
                    merchant_key=override.merchant_key,
                    category_id=category.id,
                    category_name=category.name,
                    confidence=OVERRIDE_CONFIDENCE,
                    source="override",
                )

    if alias is not None:
        category = db.get(Category, alias.category_id)
        if category is None:
            raise RuntimeError("Merchant alias refers to a missing category.")
        source = "exact_merchant" if normalize_merchant_key(normalized_description) == merchant_key else "alias"
        confidence = EXACT_MERCHANT_CONFIDENCE if source == "exact_merchant" else alias.confidence
        return CategorizationResult(
            canonical_merchant=alias.merchant_name,
            merchant_key=merchant_key,
            category_id=category.id,
            category_name=category.name,
            confidence=confidence.quantize(CONFIDENCE_QUANT, rounding=ROUND_HALF_UP),
            source=source,
        )

    for pattern, category_slug, regex_merchant in REGEX_RULES:
        if pattern.search(normalized_description):
            category = get_category_by_slug(db, category_slug)
            fallback_merchant = regex_merchant or merchant_name
            return CategorizationResult(
                canonical_merchant=fallback_merchant,
                merchant_key=merchant_key_for_name(fallback_merchant),
                category_id=category.id,
                category_name=category.name,
                confidence=REGEX_CONFIDENCE,
                source="regex",
            )

    other = get_category_by_slug(db, "other")
    return CategorizationResult(
        canonical_merchant=merchant_name,
        merchant_key=merchant_key,
        category_id=other.id,
        category_name=other.name,
        confidence=FALLBACK_CONFIDENCE,
        source="fallback",
    )


def apply_categorization_to_transaction(
    transaction: Transaction,
    result: CategorizationResult,
) -> None:
    transaction.canonical_merchant = result.canonical_merchant
    transaction.merchant_key = result.merchant_key
    transaction.category_id = result.category_id
    transaction.categorization_confidence = result.confidence
    transaction.categorization_source = result.source


def recategorize_transaction(
    db: Session,
    current_user: User,
    transaction_id: UUID,
    category_id: UUID,
    apply_to_merchant: bool,
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

    category = get_category_or_404(db, category_id)
    merchant_name = transaction.canonical_merchant
    merchant_key = transaction.merchant_key

    transaction.category_id = category.id
    transaction.categorization_confidence = OVERRIDE_CONFIDENCE
    transaction.categorization_source = "override"

    if apply_to_merchant and merchant_name and merchant_key:
        _upsert_user_override(
            db=db,
            user_id=current_user.id,
            merchant_name=merchant_name,
            merchant_key=merchant_key,
            category_id=category.id,
        )
        matching_transactions = list(
            db.scalars(
                select(Transaction).where(
                    Transaction.user_id == current_user.id,
                    Transaction.merchant_key == merchant_key,
                )
            )
        )
        for matching_transaction in matching_transactions:
            matching_transaction.category_id = category.id
            matching_transaction.categorization_confidence = OVERRIDE_CONFIDENCE
            matching_transaction.categorization_source = "override"

    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def _find_best_alias(db: Session, candidates: list[str]) -> MerchantAlias | None:
    if not candidates:
        return None

    rank = {candidate: index for index, candidate in enumerate(candidates)}
    aliases = list(
        db.scalars(
            select(MerchantAlias).where(MerchantAlias.alias_key.in_(candidates))
        )
    )
    if not aliases:
        return None

    return sorted(
        aliases,
        key=lambda alias: (
            rank.get(alias.alias_key, 999),
            -len(alias.alias_key),
            -Decimal(alias.confidence),
            alias.merchant_name,
        ),
    )[0]


def _upsert_user_override(
    *,
    db: Session,
    user_id: UUID,
    merchant_name: str,
    merchant_key: str,
    category_id: UUID,
) -> None:
    statement = (
        insert(UserMerchantOverride)
        .values(
            user_id=user_id,
            merchant_name=merchant_name,
            merchant_key=merchant_key,
            category_id=category_id,
        )
        .on_conflict_do_update(
            constraint="uq_user_merchant_overrides_user_merchant",
            set_={
                "merchant_name": merchant_name,
                "category_id": category_id,
                "updated_at": func.now(),
            },
        )
    )
    db.execute(statement)

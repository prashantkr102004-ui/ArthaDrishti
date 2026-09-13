from __future__ import annotations

import hashlib
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pymupdf
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.budget import Budget
from app.models.category import Category
from app.models.document import Document
from app.models.goal import FinancialGoal
from app.models.transaction import Transaction
from app.models.user import User

DEMO_EMAIL = os.getenv("ARTHADRISHTI_DEMO_EMAIL", "demo@arthadrishti.local")
DEMO_PASSWORD = os.getenv("ARTHADRISHTI_DEMO_PASSWORD", "demo password 123")


def _default_demo_asset_dir() -> Path:
    cwd = Path.cwd()
    if cwd.name == "backend" and cwd.parent.exists():
        return cwd.parent / "local_uploads" / "demo"
    return cwd / "local_uploads" / "demo"


DEMO_ASSET_DIR = Path(os.getenv("ARTHADRISHTI_DEMO_ASSET_DIR", str(_default_demo_asset_dir())))


def main() -> None:
    DEMO_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    statement_pdf = DEMO_ASSET_DIR / "arthadrishti-demo-statement.pdf"
    rag_pdf = DEMO_ASSET_DIR / "arthadrishti-demo-credit-card-terms.pdf"
    _write_pdf(statement_pdf, [_statement_text()])
    _write_pdf(rag_pdf, [_rag_terms_text()])

    with SessionLocal() as db:
        user = _ensure_demo_user(db)
        categories = {
            category.slug: category
            for category in db.scalars(select(Category)).all()
        }
        if not categories:
            raise RuntimeError("Categories are missing. Run Alembic migrations before seeding demo data.")

        document = _ensure_demo_document(db, user, statement_pdf.stat().st_size)
        existing = db.scalar(select(Transaction.id).where(Transaction.document_id == document.id))
        if existing is None:
            for row in _demo_transactions():
                _add_transaction(db, user, document, categories, row)

        _ensure_demo_budgets(db, user, categories)
        _ensure_demo_goal(db, user)
        db.commit()

    print("Demo seed complete.")
    print(f"Demo user: {DEMO_EMAIL}")
    print("Demo password: development/demo only, see ARTHADRISHTI_DEMO_PASSWORD override.")
    print(f"Parser demo PDF: {statement_pdf.resolve()}")
    print(f"RAG demo PDF: {rag_pdf.resolve()}")


def _ensure_demo_user(db) -> User:
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is not None:
        return user
    user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), is_active=True)
    db.add(user)
    db.flush()
    return user


def _ensure_demo_document(db, user: User, file_size_bytes: int) -> Document:
    sha = hashlib.sha256(f"{user.id}:phase-15-demo-ledger".encode("utf-8")).hexdigest()
    document = db.scalar(
        select(Document).where(
            Document.user_id == user.id,
            Document.sha256_hash == sha,
        )
    )
    if document is not None:
        return document
    document = Document(
        user_id=user.id,
        document_type="bank_statement",
        original_filename="arthadrishti-demo-ledger.pdf",
        storage_backend="local",
        storage_key=f"{user.id}/arthadrishti-demo-ledger.pdf",
        mime_type="application/pdf",
        file_size_bytes=file_size_bytes,
        sha256_hash=sha,
        processing_status="completed",
        indexing_status="not_indexed",
        uploaded_at=datetime.now(UTC),
    )
    db.add(document)
    db.flush()
    return document


def _add_transaction(db, user: User, document: Document, categories: dict[str, Category], row: dict[str, str]) -> None:
    category = categories[row["category"]]
    description = row["description"]
    merchant = row["merchant"]
    fingerprint_source = "|".join(
        [
            str(user.id),
            row["date"],
            row["amount"],
            row["direction"],
            description,
            merchant,
        ]
    )
    db.add(
        Transaction(
            user_id=user.id,
            document_id=document.id,
            transaction_date=date.fromisoformat(row["date"]),
            raw_description=description,
            normalized_description=" ".join(description.split()),
            canonical_merchant=merchant,
            merchant_key=merchant.casefold(),
            category_id=category.id,
            categorization_confidence=Decimal("1.0000"),
            categorization_source="override",
            amount=Decimal(row["amount"]),
            direction=row["direction"],
            currency="INR",
            balance=Decimal(row["balance"]) if row.get("balance") else None,
            source_page=1,
            source_row=int(row["source_row"]),
            extraction_confidence=Decimal("1.0000"),
            dedupe_fingerprint=hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest(),
        )
    )


def _ensure_demo_budgets(db, user: User, categories: dict[str, Category]) -> None:
    if db.scalar(select(Budget.id).where(Budget.user_id == user.id)) is not None:
        return
    budgets = [
        (None, "60000.0000"),
        ("food-restaurants", "9000.0000"),
        ("shopping-online", "8000.0000"),
        ("travel", "12000.0000"),
    ]
    for slug, amount in budgets:
        db.add(
            Budget(
                user_id=user.id,
                category_id=categories[slug].id if slug else None,
                amount=Decimal(amount),
                period="monthly",
                start_date=date(2026, 1, 1),
            )
        )


def _ensure_demo_goal(db, user: User) -> None:
    if db.scalar(select(FinancialGoal.id).where(FinancialGoal.user_id == user.id)) is not None:
        return
    db.add(
        FinancialGoal(
            user_id=user.id,
            name="Emergency fund",
            target_amount=Decimal("200000.0000"),
            current_saved_amount=Decimal("85000.0000"),
            target_date=date(2027, 3, 31),
            status="active",
        )
    )


def _demo_transactions() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    source_row = 1
    balances = {
        "2026-03": Decimal("60000.0000"),
        "2026-04": Decimal("62000.0000"),
        "2026-05": Decimal("65000.0000"),
        "2026-06": Decimal("67000.0000"),
        "2026-07": Decimal("70000.0000"),
        "2026-08": Decimal("72000.0000"),
        "2026-09": Decimal("73000.0000"),
    }
    monthly_rows = {
        "2026-03": [("03", "credit", "72000.0000", "Salary Credit", "Acme Payroll", "income")],
        "2026-04": [("03", "credit", "72000.0000", "Salary Credit", "Acme Payroll", "income")],
        "2026-05": [("03", "credit", "74000.0000", "Salary Credit", "Acme Payroll", "income")],
        "2026-06": [("03", "credit", "74000.0000", "Salary Credit", "Acme Payroll", "income")],
        "2026-07": [("03", "credit", "76000.0000", "Salary Credit", "Acme Payroll", "income")],
        "2026-08": [("03", "credit", "76000.0000", "Salary Credit", "Acme Payroll", "income")],
        "2026-09": [("03", "credit", "78000.0000", "Salary Credit", "Acme Payroll", "income")],
    }
    recurring_debits = [
        ("05", "debit", "22000.0000", "Rent Payment", "City Homes", "rent"),
        ("07", "debit", "799.0000", "NETFLIX.COM", "Netflix", "subscriptions"),
        ("08", "debit", "119.0000", "SPOTIFY PREMIUM", "Spotify", "subscriptions"),
        ("10", "debit", "4200.0000", "Electricity Bill", "BESCOM", "bills"),
        ("12", "debit", "3500.0000", "SWIGGY FOOD ORDER", "Swiggy", "food-restaurants"),
        ("15", "debit", "5200.0000", "AMAZON PAY INDIA", "Amazon", "shopping-online"),
        ("18", "debit", "1400.0000", "UBER TRIP BLR", "Uber", "transportation"),
        ("20", "debit", "3000.0000", "Mutual Fund SIP", "Mutual Fund", "investments"),
        ("22", "debit", "5000.0000", "Own Account Transfer", "Transfer", "transfers"),
    ]
    for month, entries in monthly_rows.items():
        entries.extend(recurring_debits)
        if month in {"2026-07", "2026-08"}:
            entries.append(("24", "debit", "10500.0000", "Weekend Trip Booking", "TravelKart", "travel"))
        if month == "2026-09":
            entries.extend([
                ("16", "debit", "8950.0000", "UBER INTERCITY PREMIUM", "Uber", "transportation"),
                ("19", "debit", "2200.0000", "Apollo Pharmacy", "Apollo Pharmacy", "healthcare"),
                ("21", "debit", "1800.0000", "Movie Tickets", "PVR Cinemas", "entertainment"),
            ])
        balance = balances[month]
        for day, direction, amount, description, merchant, category in entries:
            delta = Decimal(amount)
            balance = balance + delta if direction == "credit" else balance - delta
            rows.append(
                {
                    "date": f"{month}-{day}",
                    "direction": direction,
                    "amount": amount,
                    "description": description,
                    "merchant": merchant,
                    "category": category,
                    "balance": f"{balance:.4f}",
                    "source_row": str(source_row),
                }
            )
            source_row += 1
    return rows


def _statement_text() -> str:
    return """ARTHADRISHTI SYNTHETIC BANK STATEMENT
Bank: Artha Demo Bank
Account: XXXX-1234
Statement Period: 01/09/2026 - 30/09/2026
Opening Balance: INR 73,000.00
Currency: INR

Date | Value Date | Description | Debit | Credit | Balance
03/09/2026 | 03/09/2026 | Salary Credit | | INR 78,000.00 | INR 1,51,000.00
05/09/2026 | 05/09/2026 | Rent Payment | INR 22,000.00 | | INR 1,29,000.00
07/09/2026 | 07/09/2026 | NETFLIX.COM | INR 799.00 | | INR 1,28,201.00
12/09/2026 | 12/09/2026 | SWIGGY FOOD ORDER | INR 3,500.00 | | INR 1,24,701.00
16/09/2026 | 16/09/2026 | UBER INTERCITY PREMIUM | INR 8,950.00 | | INR 1,15,751.00
21/09/2026 | 21/09/2026 | Movie Tickets | INR 1,800.00 | | INR 1,13,951.00

Closing Balance: INR 1,13,951.00
"""


def _rag_terms_text() -> str:
    return """ARTHADRISHTI SYNTHETIC CREDIT CARD TERMS
Statement Date: 11/09/2026
Important Terms and Charges
Annual fee: INR 999 plus applicable taxes.
Late payment fee: INR 500 when payment is not received by the due date.
Interest rate: 3.5% per month on revolving balances.
Minimum payment: 5% of outstanding balance.
Cash withdrawal charges: 2.5% of amount withdrawn or INR 500, whichever is higher.
Billing address: 42 Demo Avenue, Bengaluru 560001.
"""


def _write_pdf(path: Path, pages: list[str]) -> None:
    document = pymupdf.open()
    for text in pages:
        page = document.new_page(width=595, height=842)
        page.insert_textbox((36, 36, 559, 806), text, fontsize=10, fontname="courier")
    document.save(path)
    document.close()


if __name__ == "__main__":
    main()

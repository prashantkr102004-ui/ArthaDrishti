from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.transaction import Transaction
from app.schemas.parsing import TransactionDirection
from app.services.transactions import (
    build_transaction_fingerprint,
    normalize_currency,
    normalize_description,
    normalize_money,
)
from tests.fixtures.statements import (
    make_overlapping_statement_pdf,
    make_same_day_distinct_statement_pdf,
    make_supported_statement_pdf,
)


def register_and_login(
    client: TestClient,
    email: str,
    password: str = "correct horse battery staple",
) -> str:
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def upload_pdf(
    client: TestClient,
    token: str,
    content: bytes,
    filename: str = "synthetic-statement.pdf",
):
    return client.post(
        "/api/v1/documents",
        headers=auth_headers(token),
        data={"document_type": "bank_statement"},
        files={"file": (filename, content, "application/pdf")},
    )


def parse_document(client: TestClient, token: str, document_id: str):
    return client.post(
        f"/api/v1/documents/{document_id}/parse",
        headers=auth_headers(token),
    )


def count_transactions(db_session: Session, user_id: UUID) -> int:
    return (
        db_session.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.user_id == user_id)
        )
        or 0
    )


def get_transactions_for_document(
    db_session: Session,
    document_id: str,
) -> list[Transaction]:
    return list(
        db_session.scalars(
            select(Transaction)
            .where(Transaction.document_id == UUID(document_id))
            .order_by(Transaction.source_page.asc(), Transaction.source_row.asc())
        )
    )


def test_transaction_normalization_is_deterministic() -> None:
    assert normalize_description("  UPI   SWIGGY\nBANGALORE  ") == "UPI SWIGGY BANGALORE"
    assert normalize_money(Decimal("1.23456")) == Decimal("1.2346")
    assert normalize_currency(None) == "INR"
    assert normalize_currency(" inr ") == "INR"


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-1.00")])
def test_normalized_money_rejects_non_positive_amounts(amount: Decimal) -> None:
    with pytest.raises(ValueError):
        normalize_money(amount)


def test_fingerprint_is_stable_and_uses_balance_to_avoid_bad_deduping() -> None:
    base = {
        "user_id": UUID("00000000-0000-0000-0000-000000000001"),
        "transaction_date": date(2026, 9, 10),
        "value_date": date(2026, 9, 10),
        "amount": Decimal("500.0000"),
        "direction": TransactionDirection.debit,
        "normalized_description": "ATM Withdrawal Cash",
        "currency": "INR",
    }

    first = build_transaction_fingerprint(balance=Decimal("500.0000"), **base)
    repeated = build_transaction_fingerprint(balance=Decimal("500.0000"), **base)
    second_same_day_payment = build_transaction_fingerprint(balance=Decimal("0.0000"), **base)

    assert first == repeated
    assert first != second_same_day_payment


def test_supported_statement_imports_exact_transactions(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "tx.import@example.com")
    created = upload_pdf(client, token, make_supported_statement_pdf()).json()

    response = parse_document(client, token, created["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["rows_parsed"] == 7
    assert body["inserted_count"] == 7
    assert body["duplicate_count"] == 0
    assert body["failed_count"] == 0
    assert body["transaction_count"] == 7

    rows = get_transactions_for_document(db_session, created["id"])
    assert len(rows) == 7
    assert rows[0].raw_description == "Salary Credit"
    assert rows[0].normalized_description == "Salary Credit"
    assert rows[0].direction == "credit"
    assert rows[0].amount == Decimal("50000.0000")
    assert rows[0].balance == Decimal("60000.0000")
    assert rows[0].currency == "INR"
    assert rows[0].user_id is not None
    assert rows[0].document_id == UUID(created["id"])
    assert rows[3].raw_description == "Online Transfer NEFT ABC Ref: ABC123"
    assert rows[3].direction == "debit"
    assert rows[3].amount == Decimal("1000.0000")


def test_transaction_list_detail_filters_and_pagination(client: TestClient) -> None:
    token = register_and_login(client, "tx.list@example.com")
    created = upload_pdf(client, token, make_supported_statement_pdf()).json()
    parse_document(client, token, created["id"])

    list_response = client.get("/api/v1/transactions", headers=auth_headers(token))
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] == 7
    assert list_body["limit"] == 50
    assert list_body["offset"] == 0
    assert list_body["items"][0]["transaction_date"] == "2026-08-31"
    assert list_body["items"][0]["raw_description"] == "Utilities"

    debit_response = client.get(
        "/api/v1/transactions?direction=debit",
        headers=auth_headers(token),
    )
    assert debit_response.status_code == 200
    assert debit_response.json()["total"] == 5
    assert {item["direction"] for item in debit_response.json()["items"]} == {"debit"}

    date_response = client.get(
        "/api/v1/transactions?start_date=2026-08-15&end_date=2026-08-31",
        headers=auth_headers(token),
    )
    assert date_response.status_code == 200
    assert date_response.json()["total"] == 3

    document_response = client.get(
        f"/api/v1/transactions?document_id={created['id']}",
        headers=auth_headers(token),
    )
    assert document_response.status_code == 200
    assert document_response.json()["total"] == 7

    page_response = client.get(
        "/api/v1/transactions?limit=2&offset=1",
        headers=auth_headers(token),
    )
    assert page_response.status_code == 200
    assert page_response.json()["total"] == 7
    assert len(page_response.json()["items"]) == 2

    transaction_id = list_body["items"][0]["id"]
    detail_response = client.get(
        f"/api/v1/transactions/{transaction_id}",
        headers=auth_headers(token),
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == transaction_id


def test_transaction_ownership_is_enforced(client: TestClient) -> None:
    owner_token = register_and_login(client, "tx.owner@example.com")
    other_token = register_and_login(client, "tx.other@example.com")
    created = upload_pdf(client, owner_token, make_supported_statement_pdf()).json()
    parse_document(client, owner_token, created["id"])

    owner_list = client.get("/api/v1/transactions", headers=auth_headers(owner_token)).json()
    transaction_id = owner_list["items"][0]["id"]

    other_list = client.get("/api/v1/transactions", headers=auth_headers(other_token))
    other_detail = client.get(
        f"/api/v1/transactions/{transaction_id}",
        headers=auth_headers(other_token),
    )

    assert other_list.status_code == 200
    assert other_list.json()["total"] == 0
    assert other_detail.status_code == 404


def test_reprocessing_same_document_is_idempotent(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "tx.idempotent@example.com")
    created = upload_pdf(client, token, make_supported_statement_pdf()).json()

    first = parse_document(client, token, created["id"]).json()
    second = parse_document(client, token, created["id"]).json()

    assert first["inserted_count"] == 7
    assert first["duplicate_count"] == 0
    assert second["inserted_count"] == 0
    assert second["duplicate_count"] == 7
    document = db_session.get(Document, UUID(created["id"]))
    assert document is not None
    assert count_transactions(db_session, document.user_id) == 7


def test_overlapping_statement_skips_exact_duplicate_and_keeps_new_transaction(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "tx.overlap@example.com")
    first = upload_pdf(
        client,
        token,
        make_supported_statement_pdf(),
        filename="august-statement.pdf",
    ).json()
    second = upload_pdf(
        client,
        token,
        make_overlapping_statement_pdf(),
        filename="overlap-statement.pdf",
    ).json()

    parse_document(client, token, first["id"])
    overlap_response = parse_document(client, token, second["id"])

    assert overlap_response.status_code == 200
    body = overlap_response.json()
    assert body["rows_parsed"] == 2
    assert body["inserted_count"] == 1
    assert body["duplicate_count"] == 1
    first_document = db_session.get(Document, UUID(first["id"]))
    assert first_document is not None
    assert count_transactions(db_session, first_document.user_id) == 8


def test_same_day_same_description_transactions_are_kept_when_balance_differs(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "tx.same-day@example.com")
    created = upload_pdf(client, token, make_same_day_distinct_statement_pdf()).json()

    response = parse_document(client, token, created["id"])

    assert response.status_code == 200
    assert response.json()["inserted_count"] == 2
    rows = get_transactions_for_document(db_session, created["id"])
    assert len(rows) == 2
    assert {row.balance for row in rows} == {Decimal("500.0000"), Decimal("0.0000")}


def test_document_delete_is_blocked_after_transactions_are_imported(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "tx.delete-document@example.com")
    created = upload_pdf(client, token, make_supported_statement_pdf()).json()
    parse_document(client, token, created["id"])
    document = db_session.get(Document, UUID(created["id"]))
    assert document is not None
    stored_path = settings.resolved_document_storage_path / document.storage_key
    assert stored_path.exists()

    response = client.delete(
        f"/api/v1/documents/{created['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 409
    assert db_session.get(Document, UUID(created["id"])) is not None
    assert stored_path.exists()
    assert count_transactions(db_session, document.user_id) == 7


@pytest.mark.parametrize(
    ("amount", "direction", "case_name"),
    [
        (Decimal("0.0000"), "debit", "zero"),
        (Decimal("-1.0000"), "debit", "negative"),
        (Decimal("10.0000"), "refund", "direction"),
    ],
)
def test_database_constraints_reject_invalid_canonical_transactions(
    client: TestClient,
    db_session: Session,
    amount: Decimal,
    direction: str,
    case_name: str,
) -> None:
    token = register_and_login(client, f"tx.constraint.{case_name}@example.com")
    created = upload_pdf(client, token, make_supported_statement_pdf()).json()
    document = db_session.get(Document, UUID(created["id"]))
    assert document is not None

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(
                Transaction(
                    user_id=document.user_id,
                    document_id=document.id,
                    transaction_date=date(2026, 8, 1),
                    raw_description="Invalid row",
                    normalized_description="Invalid row",
                    amount=amount,
                    direction=direction,
                    currency="INR",
                    dedupe_fingerprint=f"{amount}-{direction}"
                    .encode()
                    .hex()[:64]
                    .ljust(64, "0"),
                )
            )
            db_session.flush()

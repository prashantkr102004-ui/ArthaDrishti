from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.transaction import Transaction
from tests.fixtures.statements import (
    make_generic_bank_statement_pdf,
    make_malformed_statement_pdf,
    make_password_protected_pdf,
    make_supported_statement_pdf,
    make_textless_pdf,
    make_unsupported_statement_pdf,
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
    document_type: str = "bank_statement",
):
    return client.post(
        "/api/v1/documents",
        headers=auth_headers(token),
        data={"document_type": document_type},
        files={"file": (filename, content, "application/pdf")},
    )


def parse_document(client: TestClient, token: str, document_id: str):
    return client.post(
        f"/api/v1/documents/{document_id}/parse",
        headers=auth_headers(token),
    )


def test_owner_can_parse_supported_statement_and_get_exact_preview(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "parse.owner@example.com")
    upload_response = upload_pdf(client, token, make_supported_statement_pdf())
    assert upload_response.status_code == 201
    document_id = upload_response.json()["id"]

    response = parse_document(client, token, document_id)

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["status"] == "completed"
    assert body["result_status"] == "success"
    assert body["parser_name"] == "synthetic_bank_statement"
    assert body["parser_version"] == "1.0"
    assert body["transaction_count"] == 7
    assert body["warning_count"] == 0
    assert body["error_count"] == 0
    assert len(body["preview_transactions"]) == 5

    first = body["preview_transactions"][0]
    assert first["transaction_date"] == "2026-08-01"
    assert first["value_date"] == "2026-08-01"
    assert first["raw_description"] == "Salary Credit"
    assert Decimal(first["amount"]) == Decimal("50000.00")
    assert first["direction"] == "credit"
    assert Decimal(first["balance"]) == Decimal("60000.00")

    fourth = body["preview_transactions"][3]
    assert fourth["raw_description"] == "Online Transfer NEFT ABC Ref: ABC123"
    assert fourth["direction"] == "debit"
    assert Decimal(fourth["amount"]) == Decimal("1000.00")

    document = db_session.get(Document, UUID(document_id))
    assert document is not None
    assert document.processing_status == "completed"
    assert document.processing_error is None


def test_owner_can_parse_generic_statement_and_import_transactions(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "parse.generic@example.com")
    upload_response = upload_pdf(
        client,
        token,
        make_generic_bank_statement_pdf(),
        filename="ArthaDrishti_Demo_Bank_Statement.pdf",
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["id"]

    response = parse_document(client, token, document_id)

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["status"] == "completed"
    assert body["result_status"] == "success"
    assert body["parser_name"] == "generic_bank_statement"
    assert body["transaction_count"] == 7
    assert body["rows_parsed"] == 7
    assert body["inserted_count"] == 7
    assert body["duplicate_count"] == 0
    assert body["failed_count"] == 0

    transactions = (
        db_session.query(Transaction)
        .filter(Transaction.document_id == UUID(document_id))
        .order_by(Transaction.transaction_date.asc())
        .all()
    )
    assert [transaction.raw_description for transaction in transactions] == [
        "SALARY CREDIT - DEMO TECH PVT LTD",
        "UPI - SWIGGY FOOD ORDER",
        "UPI - UBER TRIP",
        "NETFLIX SUBSCRIPTION",
        "MUTUAL FUND SIP",
        "AMAZON REFUND",
        "UNUSUAL ELECTRONICS PURCHASE",
    ]
    salary, swiggy, _uber, netflix, mutual_fund, amazon_refund, electronics = transactions
    assert salary.direction == "credit"
    assert salary.amount == Decimal("55000.0000")
    assert swiggy.direction == "debit"
    assert swiggy.amount == Decimal("650.0000")
    assert netflix.direction == "debit"
    assert netflix.amount == Decimal("649.0000")
    assert mutual_fund.direction == "debit"
    assert mutual_fund.amount == Decimal("5000.0000")
    assert amazon_refund.direction == "credit"
    assert amazon_refund.amount == Decimal("999.0000")
    assert electronics.direction == "debit"
    assert electronics.amount == Decimal("18500.0000")
    assert swiggy.canonical_merchant == "Swiggy"
    assert netflix.canonical_merchant == "Netflix"

    index_response = client.post(
        f"/api/v1/documents/{document_id}/index",
        headers=auth_headers(token),
    )
    assert index_response.status_code == 200
    assert index_response.json()["chunks_created"] >= 1


def test_non_owner_cannot_parse_another_users_document(client: TestClient) -> None:
    owner_token = register_and_login(client, "parse.owner.only@example.com")
    other_token = register_and_login(client, "parse.other@example.com")
    created = upload_pdf(client, owner_token, make_supported_statement_pdf()).json()

    response = parse_document(client, other_token, created["id"])

    assert response.status_code == 404


def test_unsupported_valid_pdf_fails_safely(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "parse.unsupported@example.com")
    created = upload_pdf(client, token, make_unsupported_statement_pdf()).json()

    response = parse_document(client, token, created["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["result_status"] == "failed"
    assert body["errors"][0]["code"] == "unsupported_statement_format"
    assert body["transaction_count"] == 0
    document = db_session.get(Document, UUID(created["id"]))
    assert document is not None
    assert document.processing_status == "failed"
    assert document.processing_error == "This statement format is not supported yet."


def test_textless_pdf_reports_ocr_required(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "parse.textless@example.com")
    created = upload_pdf(client, token, make_textless_pdf()).json()

    response = parse_document(client, token, created["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["errors"][0]["code"] == "ocr_required"
    document = db_session.get(Document, UUID(created["id"]))
    assert document is not None
    assert document.processing_status == "failed"


def test_password_protected_pdf_fails_safely(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "parse.password@example.com")
    created = upload_pdf(client, token, make_password_protected_pdf()).json()

    response = parse_document(client, token, created["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["errors"][0]["code"] == "password_protected_pdf"
    document = db_session.get(Document, UUID(created["id"]))
    assert document is not None
    assert document.processing_status == "failed"


def test_missing_private_file_fails_safely(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "parse.missing-file@example.com")
    created = upload_pdf(client, token, make_supported_statement_pdf()).json()
    document = db_session.get(Document, UUID(created["id"]))
    assert document is not None
    stored_path = settings.resolved_document_storage_path / document.storage_key
    assert stored_path.exists()
    stored_path.unlink()

    response = parse_document(client, token, created["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["errors"][0]["code"] == "missing_document_file"
    assert "storage" not in response.text


def test_malformed_rows_return_partial_success(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "parse.malformed@example.com")
    created = upload_pdf(client, token, make_malformed_statement_pdf()).json()

    response = parse_document(client, token, created["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["result_status"] == "partial_success"
    assert body["transaction_count"] == 2
    assert body["error_count"] == 2
    assert {error["code"] for error in body["errors"]} == {
        "invalid_amount",
        "malformed_transaction_row",
    }
    document = db_session.get(Document, UUID(created["id"]))
    assert document is not None
    assert document.processing_status == "completed"


def test_parse_endpoint_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents/00000000-0000-0000-0000-000000000000/parse",
    )

    assert response.status_code == 401


def test_parser_does_not_expose_internal_storage_path(client: TestClient) -> None:
    token = register_and_login(client, "parse.no-path@example.com")
    created = upload_pdf(client, token, make_supported_statement_pdf()).json()

    response = parse_document(client, token, created["id"])

    assert response.status_code == 200
    assert "storage_key" not in response.text
    assert "storage/" not in response.text
    assert str(Path("storage")) not in response.text

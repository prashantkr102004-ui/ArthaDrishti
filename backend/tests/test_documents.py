from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document

PDF_BYTES = b"%PDF-1.4\n% Phase 5 test PDF\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


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
    filename: str = "statement.pdf",
    content: bytes = PDF_BYTES,
    document_type: str = "bank_statement",
    content_type: str = "application/pdf",
):
    return client.post(
        "/api/v1/documents",
        headers=auth_headers(token),
        data={"document_type": document_type},
        files={"file": (filename, content, content_type)},
    )


def test_authenticated_valid_pdf_upload_succeeds(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "docs.valid@example.com")

    response = upload_pdf(client, token, filename="../../statement.pdf")

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "statement.pdf"
    assert body["document_type"] == "bank_statement"
    assert body["mime_type"] == "application/pdf"
    assert body["file_size_bytes"] == len(PDF_BYTES)
    assert body["processing_status"] == "ready_for_processing"
    assert "storage_key" not in body
    assert "storage_path" not in body
    assert "sha256_hash" not in body
    assert "user_id" not in body

    document = db_session.get(Document, UUID(body["id"]))
    assert document is not None
    assert document.user_id is not None
    assert document.original_filename == "statement.pdf"
    assert document.storage_key != "statement.pdf"
    assert ".." not in document.storage_key
    assert document.sha256_hash

    stored_path = settings.resolved_document_storage_path / document.storage_key
    assert stored_path.exists()
    assert stored_path.is_file()
    assert stored_path.resolve().is_relative_to(settings.resolved_document_storage_path)


def test_unauthenticated_upload_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents",
        data={"document_type": "bank_statement"},
        files={"file": ("statement.pdf", PDF_BYTES, "application/pdf")},
    )

    assert response.status_code == 401


def test_non_pdf_extension_rejected(client: TestClient) -> None:
    token = register_and_login(client, "docs.extension@example.com")

    response = upload_pdf(client, token, filename="statement.txt")

    assert response.status_code == 415


def test_fake_pdf_rejected(client: TestClient) -> None:
    token = register_and_login(client, "docs.fake@example.com")

    response = upload_pdf(client, token, content=b"not really a pdf")

    assert response.status_code == 415


def test_oversized_pdf_rejected(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "docs.oversized@example.com")
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)
    oversized = b"%PDF-" + (b"x" * (settings.max_upload_size_bytes + 1))

    response = upload_pdf(client, token, content=oversized)

    assert response.status_code == 413


def test_unsupported_document_type_rejected(client: TestClient) -> None:
    token = register_and_login(client, "docs.unsupported@example.com")

    response = upload_pdf(client, token, document_type="receipt")

    assert response.status_code == 422


def test_duplicate_file_policy_rejects_same_user_duplicate(
    client: TestClient,
) -> None:
    token = register_and_login(client, "docs.duplicate@example.com")
    first = upload_pdf(client, token)
    second = upload_pdf(client, token, filename="same-file-again.pdf")

    assert first.status_code == 201
    assert second.status_code == 409


def test_listing_shows_only_current_users_documents_newest_first(
    client: TestClient,
) -> None:
    first_token = register_and_login(client, "docs.list.one@example.com")
    second_token = register_and_login(client, "docs.list.two@example.com")
    first = upload_pdf(client, first_token, filename="first.pdf", content=PDF_BYTES + b"1")
    second = upload_pdf(client, first_token, filename="second.pdf", content=PDF_BYTES + b"2")
    other = upload_pdf(client, second_token, filename="other.pdf", content=PDF_BYTES + b"3")

    assert first.status_code == 201
    assert second.status_code == 201
    assert other.status_code == 201

    response = client.get("/api/v1/documents", headers=auth_headers(first_token))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [item["original_filename"] for item in body["items"]] == [
        "second.pdf",
        "first.pdf",
    ]


def test_listing_filters_by_document_type(client: TestClient) -> None:
    token = register_and_login(client, "docs.filter@example.com")
    upload_pdf(client, token, filename="bank.pdf", content=PDF_BYTES + b"bank")
    upload_pdf(
        client,
        token,
        filename="card.pdf",
        content=PDF_BYTES + b"card",
        document_type="credit_card_statement",
    )

    response = client.get(
        "/api/v1/documents?document_type=credit_card_statement",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["document_type"] == "credit_card_statement"


def test_owner_can_retrieve_document(client: TestClient) -> None:
    token = register_and_login(client, "docs.detail@example.com")
    created = upload_pdf(client, token).json()

    response = client.get(
        f"/api/v1/documents/{created['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_non_owner_cannot_retrieve_document(client: TestClient) -> None:
    owner_token = register_and_login(client, "docs.owner@example.com")
    other_token = register_and_login(client, "docs.other@example.com")
    created = upload_pdf(client, owner_token).json()

    response = client.get(
        f"/api/v1/documents/{created['id']}",
        headers=auth_headers(other_token),
    )

    assert response.status_code == 404


def test_nonexistent_document_returns_404(client: TestClient) -> None:
    token = register_and_login(client, "docs.missing@example.com")

    response = client.get(
        "/api/v1/documents/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_owner_can_delete_document(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "docs.delete@example.com")
    created = upload_pdf(client, token).json()
    document = db_session.get(Document, UUID(created["id"]))
    assert document is not None
    stored_path = settings.resolved_document_storage_path / document.storage_key
    assert stored_path.exists()

    response = client.delete(
        f"/api/v1/documents/{created['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 204
    assert db_session.get(Document, UUID(created["id"])) is None
    assert not stored_path.exists()


def test_non_owner_cannot_delete_document(
    client: TestClient,
    db_session: Session,
) -> None:
    owner_token = register_and_login(client, "docs.delete.owner@example.com")
    other_token = register_and_login(client, "docs.delete.other@example.com")
    created = upload_pdf(client, owner_token).json()

    response = client.delete(
        f"/api/v1/documents/{created['id']}",
        headers=auth_headers(other_token),
    )

    assert response.status_code == 404
    assert db_session.get(Document, UUID(created["id"])) is not None


def test_delete_handles_missing_physical_file_safely(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "docs.delete.missing-file@example.com")
    created = upload_pdf(client, token).json()
    document = db_session.get(Document, UUID(created["id"]))
    assert document is not None
    stored_path = settings.resolved_document_storage_path / document.storage_key
    stored_path.unlink()

    response = client.delete(
        f"/api/v1/documents/{created['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 204
    assert db_session.get(Document, UUID(created["id"])) is None


def test_path_traversal_filename_cannot_escape_storage(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "docs.traversal@example.com")

    response = upload_pdf(client, token, filename="../../evil.pdf")

    assert response.status_code == 201
    document = db_session.scalar(select(Document))
    assert document is not None
    stored_path = settings.resolved_document_storage_path / document.storage_key
    assert stored_path.resolve().is_relative_to(settings.resolved_document_storage_path)
    assert Path(document.storage_key).name != "evil.pdf"


def test_storage_path_not_exposed_in_list_or_detail(client: TestClient) -> None:
    token = register_and_login(client, "docs.no-path@example.com")
    created = upload_pdf(client, token).json()

    list_response = client.get("/api/v1/documents", headers=auth_headers(token))
    detail_response = client.get(
        f"/api/v1/documents/{created['id']}",
        headers=auth_headers(token),
    )

    assert "storage_key" not in list_response.text
    assert "storage_key" not in detail_response.text
    assert "storage/" not in list_response.text
    assert "storage/" not in detail_response.text

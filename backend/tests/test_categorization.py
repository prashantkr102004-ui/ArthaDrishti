from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.document import Document
from app.models.transaction import Transaction
from app.models.user import User
from app.services.categorization import (
    categorize_description,
    normalize_merchant_key,
)
from app.services.transactions import normalize_description


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


def get_user(db_session: Session, email: str) -> User:
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    return user


def get_category(db_session: Session, slug: str) -> Category:
    category = db_session.scalar(select(Category).where(Category.slug == slug))
    assert category is not None
    return category


def create_document(db_session: Session, user: User) -> Document:
    document = Document(
        user_id=user.id,
        document_type="bank_statement",
        original_filename="categorization-test.pdf",
        storage_backend="local",
        storage_key=f"{user.id}/categorization-test.pdf",
        mime_type="application/pdf",
        file_size_bytes=100,
        sha256_hash=f"{user.id}".replace("-", "")[:64].ljust(64, "0"),
        processing_status="completed",
    )
    db_session.add(document)
    db_session.flush()
    return document


def create_transaction(
    db_session: Session,
    user: User,
    document: Document,
    description: str,
    amount: Decimal = Decimal("100.0000"),
) -> Transaction:
    result = categorize_description(db_session, user.id, description)
    transaction = Transaction(
        user_id=user.id,
        document_id=document.id,
        transaction_date=date(2026, 9, 1),
        raw_description=description,
        normalized_description=normalize_description(description),
        canonical_merchant=result.canonical_merchant,
        merchant_key=result.merchant_key,
        category_id=result.category_id,
        categorization_confidence=result.confidence,
        categorization_source=result.source,
        amount=amount,
        direction="debit",
        currency="INR",
        dedupe_fingerprint=f"{user.id}-{description}-{amount}".encode().hex()[:64].ljust(64, "0"),
    )
    db_session.add(transaction)
    db_session.flush()
    return transaction


def test_merchant_normalization_examples() -> None:
    assert normalize_merchant_key("UPI SWIGGY") == "SWIGGY"
    assert normalize_merchant_key("SWIGGY LIMITED") == "SWIGGY LIMITED"
    assert normalize_merchant_key("AMAZON PAY INDIA") == "AMAZON PAY INDIA"
    assert normalize_merchant_key("UBER TRIP BLR") == "UBER TRIP BLR"
    assert normalize_merchant_key("NETFLIX.COM") == "NETFLIX COM"
    assert normalize_merchant_key("APOLLO PHARMACY") == "APOLLO PHARMACY"


def test_aliases_normalize_to_expected_merchants_and_categories(
    client: TestClient,
    db_session: Session,
) -> None:
    email = "cat.aliases@example.com"
    register_and_login(client, email)
    user = get_user(db_session, email)

    examples = {
        "UPI SWIGGY BANGALORE": ("Swiggy", "Restaurants", Decimal("0.9800"), "alias"),
        "SWIGGY LIMITED": ("Swiggy", "Restaurants", Decimal("0.9800"), "alias"),
        "AMAZON SELLER SERVICES": ("Amazon", "Online", Decimal("0.9800"), "alias"),
        "UBER TRIP BLR": ("Uber", "Transportation", Decimal("0.9800"), "alias"),
        "NETFLIX.COM": ("Netflix", "Subscriptions", Decimal("0.9800"), "alias"),
        "APOLLO PHARMACY": ("Apollo Pharmacy", "Healthcare", Decimal("1.0000"), "exact_merchant"),
    }

    for description, expected in examples.items():
        result = categorize_description(db_session, user.id, description)
        assert (
            result.canonical_merchant,
            result.category_name,
            result.confidence,
            result.source,
        ) == expected


def test_category_assignment_layers(
    client: TestClient,
    db_session: Session,
) -> None:
    email = "cat.layers@example.com"
    register_and_login(client, email)
    user = get_user(db_session, email)

    exact = categorize_description(db_session, user.id, "Swiggy")
    alias = categorize_description(db_session, user.id, "UPI SWIGGY BANGALORE")
    regex = categorize_description(db_session, user.id, "Monthly Salary Credit")
    fallback = categorize_description(db_session, user.id, "Unknown Counterparty ABC")

    assert exact.source == "exact_merchant"
    assert exact.confidence == Decimal("1.0000")
    assert exact.category_name == "Restaurants"

    assert alias.source == "alias"
    assert alias.confidence == Decimal("0.9800")
    assert alias.canonical_merchant == "Swiggy"

    assert regex.source == "regex"
    assert regex.confidence == Decimal("0.8500")
    assert regex.category_name == "Income"

    assert fallback.source == "fallback"
    assert fallback.confidence == Decimal("0.4000")
    assert fallback.category_name == "Other"


def test_list_categories_api_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/categories")

    assert response.status_code == 401


def test_list_categories_api_returns_seed_data(client: TestClient) -> None:
    token = register_and_login(client, "cat.list@example.com")

    response = client.get("/api/v1/categories", headers=auth_headers(token))

    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert {"Food", "Shopping", "Income", "Other", "Groceries"}.issubset(names)


def test_user_override_updates_current_transaction_and_future_matching_merchant(
    client: TestClient,
    db_session: Session,
) -> None:
    email = "cat.override@example.com"
    token = register_and_login(client, email)
    user = get_user(db_session, email)
    document = create_document(db_session, user)
    transaction = create_transaction(db_session, user, document, "AMAZON PAY INDIA")
    groceries = get_category(db_session, "food-groceries")
    db_session.commit()

    response = client.patch(
        f"/api/v1/transactions/{transaction.id}/category",
        headers=auth_headers(token),
        json={"category_id": str(groceries.id), "apply_to_merchant": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category_id"] == str(groceries.id)
    assert body["category_name"] == "Groceries"
    assert body["categorization_confidence"] == "1.0000"
    assert body["categorization_source"] == "override"

    future = categorize_description(db_session, user.id, "AMAZON SELLER SERVICES")
    assert future.source == "override"
    assert future.category_name == "Groceries"
    assert future.canonical_merchant == "Amazon"


def test_override_can_be_limited_to_current_transaction(
    client: TestClient,
    db_session: Session,
) -> None:
    email = "cat.current-only@example.com"
    token = register_and_login(client, email)
    user = get_user(db_session, email)
    document = create_document(db_session, user)
    transaction = create_transaction(db_session, user, document, "NETFLIX.COM")
    entertainment = get_category(db_session, "entertainment")
    db_session.commit()

    response = client.patch(
        f"/api/v1/transactions/{transaction.id}/category",
        headers=auth_headers(token),
        json={"category_id": str(entertainment.id), "apply_to_merchant": False},
    )

    assert response.status_code == 200
    assert response.json()["category_name"] == "Entertainment"
    future = categorize_description(db_session, user.id, "NETFLIX.COM")
    assert future.source == "alias"
    assert future.category_name == "Subscriptions"


def test_recategorization_ownership_is_enforced(
    client: TestClient,
    db_session: Session,
) -> None:
    owner_email = "cat.owner@example.com"
    other_email = "cat.other@example.com"
    owner_token = register_and_login(client, owner_email)
    other_token = register_and_login(client, other_email)
    owner = get_user(db_session, owner_email)
    document = create_document(db_session, owner)
    transaction = create_transaction(db_session, owner, document, "UBER TRIP BLR")
    shopping = get_category(db_session, "shopping")
    db_session.commit()

    response = client.patch(
        f"/api/v1/transactions/{transaction.id}/category",
        headers=auth_headers(other_token),
        json={"category_id": str(shopping.id), "apply_to_merchant": True},
    )

    assert owner_token
    assert response.status_code == 404


def test_transaction_list_includes_merchant_and_category(
    client: TestClient,
    db_session: Session,
) -> None:
    email = "cat.response@example.com"
    token = register_and_login(client, email)
    user = get_user(db_session, email)
    document = create_document(db_session, user)
    create_transaction(db_session, user, document, "UPI SWIGGY BANGALORE")
    db_session.commit()

    response = client.get("/api/v1/transactions", headers=auth_headers(token))

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["canonical_merchant"] == "Swiggy"
    assert item["category_name"] == "Restaurants"
    assert item["categorization_confidence"] == "0.9800"
    assert item["categorization_source"] == "alias"

import hashlib
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.document import Document
from app.models.transaction import Transaction
from app.models.user import User


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


def create_document(db_session: Session, user: User, suffix: str = "analytics") -> Document:
    document = Document(
        user_id=user.id,
        document_type="bank_statement",
        original_filename=f"{suffix}.pdf",
        storage_backend="local",
        storage_key=f"{user.id}/{suffix}.pdf",
        mime_type="application/pdf",
        file_size_bytes=100,
        sha256_hash=f"{user.id}{suffix}".replace("-", "").encode().hex()[:64].ljust(64, "0"),
        processing_status="completed",
    )
    db_session.add(document)
    db_session.flush()
    return document


def create_transaction(
    db_session: Session,
    *,
    user: User,
    document: Document,
    tx_date: date,
    amount: str,
    direction: str,
    category_slug: str | None,
    description: str,
    merchant: str | None = None,
) -> Transaction:
    category = get_category(db_session, category_slug) if category_slug else None
    fingerprint_source = (
        f"{user.id}|{tx_date.isoformat()}|{amount}|{direction}|{description}|"
        f"{merchant or ''}"
    )
    transaction = Transaction(
        user_id=user.id,
        document_id=document.id,
        transaction_date=tx_date,
        raw_description=description,
        normalized_description=description,
        canonical_merchant=merchant,
        merchant_key=merchant.upper() if merchant else None,
        category_id=category.id if category else None,
        categorization_confidence=Decimal("1.0000") if category else None,
        categorization_source="override" if category else None,
        amount=Decimal(amount),
        direction=direction,
        currency="INR",
        dedupe_fingerprint=hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest(),
    )
    db_session.add(transaction)
    db_session.flush()
    return transaction


def seed_analytics_transactions(db_session: Session, user: User) -> Document:
    document = create_document(db_session, user)
    rows = [
        (date(2026, 8, 1), "50000.0000", "credit", "income", "August Salary", "Employer"),
        (date(2026, 8, 2), "1000.0000", "debit", "food-restaurants", "Swiggy August", "Swiggy"),
        (date(2026, 8, 3), "3000.0000", "debit", "shopping-online", "Amazon August", "Amazon"),
        (date(2026, 8, 4), "20000.0000", "debit", "transfers", "Own Account Transfer", "Transfer"),
        (date(2026, 8, 5), "5000.0000", "debit", "investments", "Mutual Fund SIP", "Mutual Fund"),
        (date(2026, 8, 6), "500.0000", "credit", "other", "Refund Credit", "Refund"),
        (date(2026, 9, 1), "60000.0000", "credit", "income", "September Salary", "Employer"),
        (date(2026, 9, 2), "4000.0000", "debit", "food-restaurants", "Swiggy September", "Swiggy"),
        (date(2026, 9, 3), "6000.0000", "debit", "travel", "Flight September", "Airline"),
        (date(2026, 9, 4), "1000.0000", "debit", "transfers", "Wallet Transfer", "Transfer"),
        (date(2026, 9, 5), "2000.0000", "debit", "investments", "September SIP", "Mutual Fund"),
    ]
    for tx_date, amount, direction, category, description, merchant in rows:
        create_transaction(
            db_session,
            user=user,
            document=document,
            tx_date=tx_date,
            amount=amount,
            direction=direction,
            category_slug=category,
            description=description,
            merchant=merchant,
        )
    db_session.commit()
    return document


def test_summary_defines_income_expenses_savings_cash_flow_and_exclusions(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "analytics.summary@example.com")
    user = get_user(db_session, "analytics.summary@example.com")
    seed_analytics_transactions(db_session, user)

    response = client.get(
        "/api/v1/analytics/summary?start_date=2026-08-01&end_date=2026-08-31",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == {
        "start_date": "2026-08-01",
        "end_date": "2026-08-31",
        "total_income": "50000.0000",
        "total_expenses": "4000.0000",
        "savings": "46000.0000",
        "savings_rate_percent": "92.0000",
        "total_debits": "29000.0000",
        "total_credits": "50500.0000",
        "raw_net_flow": "21500.0000",
        "investment_amount": "5000.0000",
        "transaction_count": 6,
    }


def test_summary_preserves_decimal_precision(client: TestClient, db_session: Session) -> None:
    token = register_and_login(client, "analytics.decimal@example.com")
    user = get_user(db_session, "analytics.decimal@example.com")
    document = create_document(db_session, user, "decimal")
    create_transaction(
        db_session,
        user=user,
        document=document,
        tx_date=date(2026, 9, 1),
        amount="0.1000",
        direction="debit",
        category_slug="food-restaurants",
        description="Small debit 1",
        merchant="Cafe",
    )
    create_transaction(
        db_session,
        user=user,
        document=document,
        tx_date=date(2026, 9, 1),
        amount="0.2000",
        direction="debit",
        category_slug="food-restaurants",
        description="Small debit 2",
        merchant="Cafe",
    )
    db_session.commit()

    response = client.get(
        "/api/v1/analytics/summary?start_date=2026-09-01&end_date=2026-09-30",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["total_expenses"] == "0.3000"
    assert response.json()["savings"] == "-0.3000"
    assert response.json()["savings_rate_percent"] is None


def test_category_spending_totals_percentages_sorting_and_exclusions(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "analytics.categories@example.com")
    user = get_user(db_session, "analytics.categories@example.com")
    seed_analytics_transactions(db_session, user)

    response = client.get(
        "/api/v1/analytics/categories?start_date=2026-08-01&end_date=2026-08-31",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_expenses"] == "4000.0000"
    assert [item["category_name"] for item in body["items"]] == ["Online", "Restaurants"]
    assert body["items"][0]["amount"] == "3000.0000"
    assert body["items"][0]["percentage_of_total_expenses"] == "75.0000"
    assert body["items"][1]["amount"] == "1000.0000"
    assert body["items"][1]["percentage_of_total_expenses"] == "25.0000"


def test_monthly_analytics_returns_exact_values_across_months(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "analytics.monthly@example.com")
    user = get_user(db_session, "analytics.monthly@example.com")
    seed_analytics_transactions(db_session, user)

    response = client.get(
        "/api/v1/analytics/monthly?start_date=2026-08-01&end_date=2026-09-30",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "month": "2026-08",
            "income": "50000.0000",
            "expenses": "4000.0000",
            "savings": "46000.0000",
            "investments": "5000.0000",
            "total_debits": "29000.0000",
            "total_credits": "50500.0000",
            "raw_net_flow": "21500.0000",
            "transaction_count": 6,
        },
        {
            "month": "2026-09",
            "income": "60000.0000",
            "expenses": "10000.0000",
            "savings": "50000.0000",
            "investments": "2000.0000",
            "total_debits": "13000.0000",
            "total_credits": "60000.0000",
            "raw_net_flow": "47000.0000",
            "transaction_count": 5,
        },
    ]


def test_top_merchants_ranks_expense_merchants_and_excludes_transfers(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "analytics.merchants@example.com")
    user = get_user(db_session, "analytics.merchants@example.com")
    seed_analytics_transactions(db_session, user)

    response = client.get(
        "/api/v1/analytics/merchants?start_date=2026-09-01&end_date=2026-09-30&limit=2",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["items"] == [
        {"merchant_name": "Airline", "amount": "6000.0000", "transaction_count": 1},
        {"merchant_name": "Swiggy", "amount": "4000.0000", "transaction_count": 1},
    ]


def test_period_comparison_and_category_deltas(
    client: TestClient,
    db_session: Session,
) -> None:
    token = register_and_login(client, "analytics.compare@example.com")
    user = get_user(db_session, "analytics.compare@example.com")
    seed_analytics_transactions(db_session, user)

    response = client.get(
        "/api/v1/analytics/compare"
        "?period_a_start=2026-09-01&period_a_end=2026-09-30"
        "&period_b_start=2026-08-01&period_b_end=2026-08-31",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["expense_period_a"] == "10000.0000"
    assert body["expense_period_b"] == "4000.0000"
    assert body["expense_difference"] == "6000.0000"
    assert body["expense_percentage_change"] == "150.0000"
    assert body["income_difference"] == "10000.0000"
    assert body["savings_difference"] == "4000.0000"
    deltas = {item["category_name"]: item for item in body["category_deltas"]}
    assert deltas["Travel"]["difference"] == "6000.0000"
    assert deltas["Restaurants"]["difference"] == "3000.0000"
    assert deltas["Online"]["difference"] == "-3000.0000"
    assert deltas["Travel"]["percentage_change"] is None


def test_empty_data_and_invalid_date_ranges_are_safe(client: TestClient) -> None:
    token = register_and_login(client, "analytics.empty@example.com")

    empty = client.get(
        "/api/v1/analytics/summary?start_date=2026-01-01&end_date=2026-01-31",
        headers=auth_headers(token),
    )
    invalid = client.get(
        "/api/v1/analytics/summary?start_date=2026-02-01&end_date=2026-01-31",
        headers=auth_headers(token),
    )

    assert empty.status_code == 200
    assert empty.json()["transaction_count"] == 0
    assert empty.json()["total_income"] == "0.0000"
    assert empty.json()["savings_rate_percent"] is None
    assert invalid.status_code == 422


def test_analytics_are_isolated_by_authenticated_user(
    client: TestClient,
    db_session: Session,
) -> None:
    owner_token = register_and_login(client, "analytics.owner@example.com")
    other_token = register_and_login(client, "analytics.other@example.com")
    owner = get_user(db_session, "analytics.owner@example.com")
    other = get_user(db_session, "analytics.other@example.com")
    seed_analytics_transactions(db_session, owner)
    other_document = create_document(db_session, other, "other")
    create_transaction(
        db_session,
        user=other,
        document=other_document,
        tx_date=date(2026, 8, 10),
        amount="9999.0000",
        direction="debit",
        category_slug="food-restaurants",
        description="Other user food",
        merchant="Other Cafe",
    )
    db_session.commit()

    owner_summary = client.get(
        "/api/v1/analytics/summary?start_date=2026-08-01&end_date=2026-08-31",
        headers=auth_headers(owner_token),
    )
    other_categories = client.get(
        "/api/v1/analytics/categories?start_date=2026-08-01&end_date=2026-08-31",
        headers=auth_headers(other_token),
    )

    assert owner_summary.status_code == 200
    assert owner_summary.json()["total_expenses"] == "4000.0000"
    assert other_categories.status_code == 200
    assert other_categories.json()["total_expenses"] == "9999.0000"
    assert other_categories.json()["items"][0]["category_name"] == "Restaurants"


def test_analytics_endpoints_require_authentication(client: TestClient) -> None:
    response = client.get(
        "/api/v1/analytics/summary?start_date=2026-08-01&end_date=2026-08-31"
    )

    assert response.status_code == 401

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.schemas.goal import AffordabilityRequest, GoalCreate
from app.services.advanced import (
    AdvancedDateRange,
    forecast_spending,
    get_financial_anomalies,
    get_recurring_payments,
    get_subscriptions,
)
from app.services.goals import check_affordability, create_goal
from tests.test_analytics import create_document, create_transaction, get_category, get_user, register_and_login
from tests.test_documents import auth_headers


def seed_advanced_transactions(db_session: Session, email: str):
    user = get_user(db_session, email)
    document = create_document(db_session, user, "advanced")

    rows = [
        (date(2026, 1, 5), "50000.0000", "credit", "income", "Salary Jan", "Employer"),
        (date(2026, 1, 10), "799.0000", "debit", "subscriptions", "Netflix Jan", "Netflix"),
        (date(2026, 1, 12), "1850.0000", "debit", "bills", "Electricity Jan", "Electricity Board"),
        (date(2026, 1, 1), "25000.0000", "debit", "rent", "Rent Jan", "Landlord"),
        (date(2026, 1, 20), "3000.0000", "debit", "shopping-online", "Amazon", "Amazon"),
        (date(2026, 2, 5), "50000.0000", "credit", "income", "Salary Feb", "Employer"),
        (date(2026, 2, 9), "799.0000", "debit", "subscriptions", "Netflix Feb", "Netflix"),
        (date(2026, 2, 11), "1920.0000", "debit", "bills", "Electricity Feb", "Electricity Board"),
        (date(2026, 2, 1), "25000.0000", "debit", "rent", "Rent Feb", "Landlord"),
        (date(2026, 2, 18), "3200.0000", "debit", "food-restaurants", "Food Feb", "Swiggy"),
        (date(2026, 3, 5), "50000.0000", "credit", "income", "Salary Mar", "Employer"),
        (date(2026, 3, 11), "799.0000", "debit", "subscriptions", "Netflix Mar", "Netflix"),
        (date(2026, 3, 13), "1875.0000", "debit", "bills", "Electricity Mar", "Electricity Board"),
        (date(2026, 3, 1), "25000.0000", "debit", "rent", "Rent Mar", "Landlord"),
        (date(2026, 3, 18), "4200.0000", "debit", "travel", "Travel Mar", "Airline"),
        (date(2026, 4, 5), "50000.0000", "credit", "income", "Salary Apr", "Employer"),
        (date(2026, 4, 10), "799.0000", "debit", "subscriptions", "Netflix Apr", "Netflix"),
        (date(2026, 4, 12), "1950.0000", "debit", "bills", "Electricity Apr", "Electricity Board"),
        (date(2026, 4, 1), "25000.0000", "debit", "rent", "Rent Apr", "Landlord"),
        (date(2026, 4, 19), "3000.0000", "debit", "food-restaurants", "Food Apr", "Swiggy"),
        (date(2026, 5, 5), "50000.0000", "credit", "income", "Salary May", "Employer"),
        (date(2026, 5, 10), "799.0000", "debit", "subscriptions", "Netflix May", "Netflix"),
        (date(2026, 5, 12), "1900.0000", "debit", "bills", "Electricity May", "Electricity Board"),
        (date(2026, 5, 1), "25000.0000", "debit", "rent", "Rent May", "Landlord"),
        (date(2026, 5, 20), "420.0000", "debit", "transportation", "Uber normal 1", "Uber"),
        (date(2026, 5, 21), "450.0000", "debit", "transportation", "Uber normal 2", "Uber"),
        (date(2026, 5, 22), "390.0000", "debit", "transportation", "Uber normal 3", "Uber"),
        (date(2026, 5, 23), "8950.0000", "debit", "transportation", "Uber airport", "Uber"),
        (date(2026, 6, 5), "50000.0000", "credit", "income", "Salary Jun", "Employer"),
        (date(2026, 6, 10), "799.0000", "debit", "subscriptions", "Netflix Jun", "Netflix"),
        (date(2026, 6, 12), "1880.0000", "debit", "bills", "Electricity Jun", "Electricity Board"),
        (date(2026, 6, 1), "25000.0000", "debit", "rent", "Rent Jun", "Landlord"),
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
    return user, document


def test_recurring_detection_handles_subscription_variable_bill_and_rent(
    client: TestClient,
    db_session: Session,
) -> None:
    register_and_login(client, "advanced.recurring@example.com")
    user, _ = seed_advanced_transactions(db_session, "advanced.recurring@example.com")

    result = get_recurring_payments(db_session, user, today=date(2026, 6, 20))
    merchants = {item.merchant: item for item in result.items}

    assert merchants["Netflix"].frequency == "monthly"
    assert merchants["Netflix"].average_amount == Decimal("799.0000")
    assert merchants["Netflix"].is_subscription is True
    assert merchants["Electricity Board"].frequency == "monthly"
    assert merchants["Electricity Board"].average_amount == Decimal("1895.8333")
    assert merchants["Electricity Board"].is_subscription is False
    assert merchants["Landlord"].is_subscription is False
    assert "Amazon" not in merchants


def test_subscription_detection_and_totals(client: TestClient, db_session: Session) -> None:
    register_and_login(client, "advanced.subscriptions@example.com")
    user, _ = seed_advanced_transactions(db_session, "advanced.subscriptions@example.com")

    result = get_subscriptions(db_session, user, today=date(2026, 6, 20))

    assert len(result.items) == 1
    assert result.items[0].merchant == "Netflix"
    assert result.items[0].estimated_monthly_cost == Decimal("799.0000")
    assert result.total_estimated_monthly_cost == Decimal("799.0000")


def test_budget_crud_progress_and_ownership(client: TestClient, db_session: Session) -> None:
    token = register_and_login(client, "advanced.budget@example.com")
    other_token = register_and_login(client, "advanced.budget.other@example.com")
    seed_advanced_transactions(db_session, "advanced.budget@example.com")
    food = get_category(db_session, "food-restaurants")

    created = client.post(
        "/api/v1/budgets",
        headers=auth_headers(token),
        json={"category_id": str(food.id), "amount": "3000.0000", "start_date": "2026-06-01"},
    )
    overall = client.post(
        "/api/v1/budgets",
        headers=auth_headers(token),
        json={"amount": "25000.0000", "start_date": "2026-06-01"},
    )
    progress = client.get(
        "/api/v1/budgets/progress?start_date=2026-04-01&end_date=2026-04-30",
        headers=auth_headers(token),
    )
    cross_user = client.patch(
        f"/api/v1/budgets/{created.json()['id']}",
        headers=auth_headers(other_token),
        json={"amount": "5000.0000"},
    )
    invalid = client.post(
        "/api/v1/budgets",
        headers=auth_headers(token),
        json={"amount": "0.0000", "start_date": "2026-06-01"},
    )

    assert created.status_code == 201
    assert overall.status_code == 201
    assert progress.status_code == 200
    statuses = {item["category_name"]: item["status"] for item in progress.json()["items"]}
    assert statuses["Restaurants"] == "near_limit"
    assert statuses["Overall spending"] == "exceeded"
    assert cross_user.status_code == 404
    assert invalid.status_code == 422


def test_goal_calculation_affordability_and_ownership(client: TestClient, db_session: Session) -> None:
    token = register_and_login(client, "advanced.goal@example.com")
    other_token = register_and_login(client, "advanced.goal.other@example.com")
    user, _ = seed_advanced_transactions(db_session, "advanced.goal@example.com")

    goal = create_goal(
        db_session,
        user,
        GoalCreate(
            name="Vacation",
            target_amount=Decimal("100000.0000"),
            target_date=date(2026, 12, 31),
            current_saved_amount=Decimal("20000.0000"),
        ),
    )
    affordability = check_affordability(
        db_session,
        user,
        AffordabilityRequest(
            name="Trip",
            target_amount=Decimal("100000.0000"),
            target_date=date(2026, 12, 31),
            current_saved_amount=Decimal("20000.0000"),
        ),
        today=date(2026, 6, 15),
    )
    cross_user = client.patch(
        f"/api/v1/goals/{goal.id}",
        headers=auth_headers(other_token),
        json={"name": "Nope"},
    )

    assert goal.remaining_amount == Decimal("80000.0000")
    assert goal.progress_percentage == Decimal("20.0000")
    assert goal.required_monthly_saving is not None
    assert goal.recommendation
    assert affordability.required_monthly_saving == Decimal("13333.3333")
    assert affordability.historical_monthly_savings is not None
    assert affordability.feasibility in {"likely_on_track", "needs_adjustment"}
    assert cross_user.status_code == 404


def test_forecast_requires_history_and_projects_next_month(client: TestClient, db_session: Session) -> None:
    register_and_login(client, "advanced.forecast@example.com")
    user, _ = seed_advanced_transactions(db_session, "advanced.forecast@example.com")
    register_and_login(client, "advanced.forecast.empty@example.com")
    empty_user = get_user(db_session, "advanced.forecast.empty@example.com")

    insufficient = forecast_spending(db_session, empty_user, today=date(2026, 7, 1))
    forecast = forecast_spending(db_session, user, today=date(2026, 7, 1))

    assert insufficient.status == "insufficient_history"
    assert insufficient.history_required_months == 3
    assert insufficient.months_missing == 3
    assert "I found 0" in insufficient.explanation
    assert forecast.status == "ready"
    assert forecast.history_required_months == 3
    assert forecast.months_missing == 0
    assert forecast.months_used >= 3
    assert forecast.projected_next_month_expenses is not None
    assert forecast.lower_estimate is not None
    assert forecast.upper_estimate is not None


def test_anomaly_detection_flags_large_merchant_transaction_not_normal_ones(
    client: TestClient,
    db_session: Session,
) -> None:
    register_and_login(client, "advanced.anomaly@example.com")
    user, _ = seed_advanced_transactions(db_session, "advanced.anomaly@example.com")

    result = get_financial_anomalies(
        db_session,
        user,
        AdvancedDateRange(date(2026, 5, 1), date(2026, 5, 31)),
    )

    assert len(result.items) == 1
    assert result.items[0].merchant == "Uber"
    assert result.items[0].amount == Decimal("8950.0000")
    assert "unusually high" in result.items[0].reason
    assert "fraud" not in result.items[0].reason.casefold()


def test_advanced_endpoints_are_user_isolated(client: TestClient, db_session: Session) -> None:
    owner_token = register_and_login(client, "advanced.owner@example.com")
    other_token = register_and_login(client, "advanced.other@example.com")
    seed_advanced_transactions(db_session, "advanced.owner@example.com")

    owner_recurring = client.get("/api/v1/advanced/recurring-payments", headers=auth_headers(owner_token))
    other_recurring = client.get("/api/v1/advanced/recurring-payments", headers=auth_headers(other_token))
    owner_anomalies = client.get(
        "/api/v1/advanced/anomalies?start_date=2026-05-01&end_date=2026-05-31",
        headers=auth_headers(owner_token),
    )
    other_anomalies = client.get(
        "/api/v1/advanced/anomalies?start_date=2026-05-01&end_date=2026-05-31",
        headers=auth_headers(other_token),
    )

    assert owner_recurring.status_code == 200
    assert len(owner_recurring.json()["items"]) >= 3
    assert other_recurring.status_code == 200
    assert other_recurring.json()["items"] == []
    assert owner_anomalies.json()["items"]
    assert other_anomalies.json()["items"] == []


def test_advanced_assistant_tools_route_to_backend_calculations(
    client: TestClient,
    db_session: Session,
) -> None:
    register_and_login(client, "advanced.assistant@example.com")
    user, _ = seed_advanced_transactions(db_session, "advanced.assistant@example.com")

    from app.assistant.orchestrator import answer_financial_question

    subscriptions = answer_financial_question(
        db=db_session,
        current_user=user,
        question="What subscriptions am I paying for?",
        today=date(2026, 6, 20),
    )
    forecast = answer_financial_question(
        db=db_session,
        current_user=user,
        question="What might I spend next month?",
        today=date(2026, 6, 20),
    )
    anomalies = answer_financial_question(
        db=db_session,
        current_user=user,
        question="Was anything unusual in my transactions this month?",
        today=date(2026, 5, 20),
    )

    assert subscriptions.tools_used == ["get_subscriptions"]
    assert forecast.tools_used == ["forecast_spending"]
    assert anomalies.tools_used == ["get_financial_anomalies"]

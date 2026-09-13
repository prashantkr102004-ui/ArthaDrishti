from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import User


def register_user(
    client: TestClient,
    email: str = "User@Example.com ",
    password: str = "correct horse battery staple",
) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201
    return response.json()


def login_user(
    client: TestClient,
    email: str = "user@example.com",
    password: str = "correct horse battery staple",
) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    return body["access_token"]


def test_successful_registration_returns_safe_user(client: TestClient) -> None:
    body = register_user(client)

    assert body["email"] == "user@example.com"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body
    assert "password" not in body
    assert "password_hash" not in body


def test_duplicate_email_rejected(client: TestClient) -> None:
    register_user(client)

    response = client.post(
        "/api/v1/auth/register",
        json={"email": " USER@example.com", "password": "another good password"},
    )

    assert response.status_code == 409


def test_invalid_email_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "correct horse battery staple"},
    )

    assert response.status_code == 422


def test_invalid_password_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "short"},
    )

    assert response.status_code == 422


def test_password_hash_is_not_plaintext(
    client: TestClient,
    db_session: Session,
) -> None:
    register_user(client)

    user = db_session.scalar(select(User).where(User.email == "user@example.com"))

    assert user is not None
    assert user.password_hash != "correct horse battery staple"
    assert user.password_hash.startswith("$argon2id$")


def test_login_with_correct_credentials_succeeds(client: TestClient) -> None:
    register_user(client)

    token = login_user(client)

    assert token.count(".") == 2


def test_login_with_wrong_password_fails(client: TestClient) -> None:
    register_user(client)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_with_unknown_email_fails_safely(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "wrong password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_inactive_user_cannot_login(
    client: TestClient,
    db_session: Session,
) -> None:
    register_user(client)
    user = db_session.scalar(select(User).where(User.email == "user@example.com"))
    assert user is not None
    user.is_active = False
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_current_user_accepts_valid_token(client: TestClient) -> None:
    register_user(client)
    token = login_user(client)

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
    assert "password_hash" not in response.json()


def test_current_user_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_current_user_rejects_malformed_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not-a-token"},
    )

    assert response.status_code == 401


def test_current_user_rejects_expired_token(
    client: TestClient,
    db_session: Session,
) -> None:
    register_user(client)
    user = db_session.scalar(select(User).where(User.email == "user@example.com"))
    assert user is not None
    token = create_access_token(user.id, expires_delta=timedelta(seconds=-1))

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401

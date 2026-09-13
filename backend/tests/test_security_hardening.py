import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.middleware import RateLimitRule, api_rate_limiter
from app.main import app


def test_security_headers_and_request_id_are_added() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "security-test-request"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "security-test-request"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"


def test_sensitive_endpoint_rate_limit_returns_safe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api_rate_limiter,
        "rules",
        [RateLimitRule(frozenset({"POST"}), "/api/v1/auth/login", 2, 60)],
    )
    api_rate_limiter.reset()

    with TestClient(app) as client:
        first = client.post("/api/v1/auth/login", json={})
        second = client.post("/api/v1/auth/login", json={})
        third = client.post("/api/v1/auth/login", json={})

    api_rate_limiter.reset()

    assert first.status_code == 422
    assert second.status_code == 422
    assert third.status_code == 429
    assert third.json()["detail"] == "Too many requests. Please try again shortly."
    assert "Retry-After" in third.headers


def test_production_config_rejects_debug_and_weak_jwt_secret() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            APP_ENV="production",
            DEBUG=True,
            DATABASE_URL="postgresql+psycopg://user:pass@db:5432/app",
            JWT_SECRET_KEY="replace-with-a-long-random-secret",
        )

    message = str(exc_info.value)
    assert "DEBUG must be false in production" in message
    assert "JWT_SECRET_KEY must be a strong production secret" in message


def test_production_config_rejects_malformed_database_url() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            APP_ENV="production",
            DEBUG=False,
            DATABASE_URL="not a database url",
            JWT_SECRET_KEY="this-is-a-long-production-style-test-secret",
        )

    assert "DATABASE_URL must be a valid SQLAlchemy database URL" in str(exc_info.value)

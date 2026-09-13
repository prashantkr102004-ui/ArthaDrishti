from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "arthadrishti-api",
    }


def test_api_v1_root() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "api_version": "v1",
    }


def test_database_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "reachable",
    }

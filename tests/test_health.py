import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_health_status_code(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_structure(client: TestClient) -> None:
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "request_id" in data


def test_health_status_value(client: TestClient) -> None:
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "ok"


def test_health_database_connected(client: TestClient) -> None:
    response = client.get("/health")
    data = response.json()
    assert data["database"] == "connected"

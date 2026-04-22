import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from tests.integration.auth_helpers import apply_mock_auth
from app.database.session import Base
from app.api.routes.understand_requirement import get_understanding_service
from app.repositories.requirement_repository import RequirementRepository
from app.services.ai_provider import StubAIProvider
from app.services.ai_requirement_parser import AIRequirementParser
from app.services.requirement_understanding_service import RequirementUnderstandingService


def make_client() -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def override() -> RequirementUnderstandingService:
        db = Session()
        repo = RequirementRepository(db)
        parser = AIRequirementParser(StubAIProvider())
        return RequirementUnderstandingService(parser, repo)

    app = apply_mock_auth(create_app())
    app.dependency_overrides[get_understanding_service] = override
    return TestClient(app)


@pytest.fixture
def client():
    return make_client()


def test_understand_requirement_returns_200(client):
    response = client.post(
        "/api/v1/understand-requirement",
        json={"requirement": "El usuario debe poder registrarse con email", "project_id": "user-service"},
    )
    assert response.status_code == 200


def test_response_contains_required_fields(client):
    response = client.post(
        "/api/v1/understand-requirement",
        json={"requirement": "El usuario debe poder registrarse con email", "project_id": "user-service"},
    )
    data = response.json()
    assert "requirement_id" in data
    assert "intent" in data
    assert "feature_type" in data
    assert "estimated_complexity" in data
    assert "processing_time_seconds" in data
    assert "request_id" in data


def test_response_ids_are_valid_uuids(client):
    response = client.post(
        "/api/v1/understand-requirement",
        json={"requirement": "Add email validation", "project_id": "test"},
    )
    assert response.status_code == 200
    data = response.json()
    uuid.UUID(data["requirement_id"])
    uuid.UUID(data["request_id"])


def test_empty_requirement_returns_400(client):
    response = client.post(
        "/api/v1/understand-requirement",
        json={"requirement": "", "project_id": "test"},
    )
    assert response.status_code == 400


def test_requirement_too_long_returns_400(client):
    response = client.post(
        "/api/v1/understand-requirement",
        json={"requirement": "x" * 2001, "project_id": "test"},
    )
    assert response.status_code == 400

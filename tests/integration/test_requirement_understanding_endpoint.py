import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from tests.integration.auth_helpers import (
    apply_mock_auth,
    seed_source_connection,
    TEST_CONNECTION_ID,
)
from app.core.config import Settings
from app.database.session import Base, get_db
from app.domain.coherence_result import CoherenceResult
from app.api.routes.understand_requirement import get_understanding_service
from app.repositories.incoherent_requirement_repository import IncoherentRequirementRepository
from app.repositories.requirement_repository import RequirementRepository
from app.services.ai_provider import StubAIProvider
from app.services.ai_requirement_parser import AIRequirementParser
from app.services.requirement_coherence_validator import RequirementCoherenceValidator
from app.services.requirement_understanding_service import RequirementUnderstandingService


class _FakeValidator(RequirementCoherenceValidator):
    model_name = "fake-test-model"

    def __init__(self, result: CoherenceResult) -> None:
        self._result = result

    def validate(self, requirement_text: str) -> CoherenceResult:
        return self._result


def make_client(validator: RequirementCoherenceValidator | None = None) -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    seed_db = Session()
    seed_source_connection(seed_db)
    seed_db.close()

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    def override() -> RequirementUnderstandingService:
        db = Session()
        repo = RequirementRepository(db)
        parser = AIRequirementParser(StubAIProvider())
        incoherent_repo = IncoherentRequirementRepository(db)
        settings = Settings(COHERENCE_VALIDATION_ENABLED=validator is not None)
        return RequirementUnderstandingService(
            parser, repo, settings, validator, incoherent_repo
        )

    app = apply_mock_auth(create_app())
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_understanding_service] = override
    return TestClient(app), Session


@pytest.fixture
def client():
    c, _session = make_client()
    return c


def test_understand_requirement_returns_200(client):
    response = client.post(
        "/api/v1/understand-requirement",
        json={
            "requirement": "El usuario debe poder registrarse con email",
            "project_id": "user-service",
            "source_connection_id": TEST_CONNECTION_ID,
        },
    )
    assert response.status_code == 200


def test_response_contains_required_fields(client):
    response = client.post(
        "/api/v1/understand-requirement",
        json={
            "requirement": "El usuario debe poder registrarse con email",
            "project_id": "user-service",
            "source_connection_id": TEST_CONNECTION_ID,
        },
    )
    data = response.json()
    assert "requirement_id" in data
    assert data["source_connection_id"] == TEST_CONNECTION_ID
    assert "intent" in data
    assert "feature_type" in data
    assert "estimated_complexity" in data
    assert "processing_time_seconds" in data
    assert "request_id" in data


def test_response_ids_are_valid_uuids(client):
    response = client.post(
        "/api/v1/understand-requirement",
        json={
            "requirement": "Add email validation",
            "project_id": "test",
            "source_connection_id": TEST_CONNECTION_ID,
        },
    )
    assert response.status_code == 200
    data = response.json()
    uuid.UUID(data["requirement_id"])
    uuid.UUID(data["request_id"])


def test_empty_requirement_returns_400(client):
    response = client.post(
        "/api/v1/understand-requirement",
        json={
            "requirement": "",
            "project_id": "test",
            "source_connection_id": TEST_CONNECTION_ID,
        },
    )
    assert response.status_code == 400


def test_requirement_too_long_returns_400(client):
    response = client.post(
        "/api/v1/understand-requirement",
        json={
            "requirement": "x" * 2001,
            "project_id": "test",
            "source_connection_id": TEST_CONNECTION_ID,
        },
    )
    assert response.status_code == 400


def test_missing_connection_returns_422(client):
    response = client.post(
        "/api/v1/understand-requirement",
        json={"requirement": "add login", "project_id": "test"},
    )
    # Pydantic 422 por campo requerido ausente
    assert response.status_code == 422


def test_invalid_connection_returns_404(client):
    response = client.post(
        "/api/v1/understand-requirement",
        json={
            "requirement": "add login",
            "project_id": "test",
            "source_connection_id": "non-existent-connection",
        },
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Coherence pre-filter — endpoint integration tests
# ---------------------------------------------------------------------------


def test_incoherent_requirement_returns_400_with_rich_body():
    validator = _FakeValidator(
        CoherenceResult(
            is_coherent=False,
            warning="El texto describe una escena, no software.",
            reason_codes=["non_software_request"],
        )
    )
    c, _Session = make_client(validator=validator)
    response = c.post(
        "/api/v1/understand-requirement",
        json={
            "requirement": "una casa roja al amanecer en la tarde de la playa",
            "project_id": "test",
            "source_connection_id": TEST_CONNECTION_ID,
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert isinstance(detail, dict)
    assert detail["code"] == "INCOHERENT_REQUIREMENT"
    assert "escena" in detail["message"]
    assert "non_software_request" in detail["reason_codes"]


def test_incoherent_requirement_persisted_in_db():
    validator = _FakeValidator(
        CoherenceResult(
            is_coherent=False,
            warning="No es accionable.",
            reason_codes=["unintelligible"],
        )
    )
    c, Session = make_client(validator=validator)
    response = c.post(
        "/api/v1/understand-requirement",
        json={
            "requirement": "asdfg qwerty",
            "project_id": "p1",
            "source_connection_id": TEST_CONNECTION_ID,
        },
    )
    assert response.status_code == 400

    db = Session()
    try:
        from app.core.context import current_tenant_id
        from tests.integration.auth_helpers import TEST_TENANT_ID
        token = current_tenant_id.set(TEST_TENANT_ID)
        try:
            rows, total = IncoherentRequirementRepository(db).list_with_user(
                limit=10, offset=0
            )
        finally:
            current_tenant_id.reset(token)
    finally:
        db.close()

    assert total == 1
    record, _email = rows[0]
    assert record.requirement_text == "asdfg qwerty"
    assert record.project_id == "p1"
    assert "unintelligible" in record.reason_codes


def test_coherent_requirement_passes_filter_and_returns_200():
    validator = _FakeValidator(
        CoherenceResult(is_coherent=True, warning=None, reason_codes=[])
    )
    c, _Session = make_client(validator=validator)
    response = c.post(
        "/api/v1/understand-requirement",
        json={
            "requirement": "Quiero login con Google y Microsoft",
            "project_id": "auth",
            "source_connection_id": TEST_CONNECTION_ID,
        },
    )
    assert response.status_code == 200


def test_validator_failure_fails_open_to_parser():
    """Si el validator lanza, el parser principal corre y devuelve 200."""
    class _BoomValidator(RequirementCoherenceValidator):
        model_name = "boom"

        def validate(self, requirement_text: str) -> CoherenceResult:
            raise RuntimeError("network exploded")

    c, _Session = make_client(validator=_BoomValidator())
    response = c.post(
        "/api/v1/understand-requirement",
        json={
            "requirement": "Add password reset by email",
            "project_id": "auth",
            "source_connection_id": TEST_CONNECTION_ID,
        },
    )
    assert response.status_code == 200

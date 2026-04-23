import json
import uuid
import hashlib
from datetime import datetime, timezone
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
    TEST_TENANT_ID,
)
from app.database.session import Base, get_db
from app.api.routes.story_generation import get_story_service
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.repositories.user_story_repository import UserStoryRepository
from app.services.ai_story_generator import AIStoryGenerator
from app.services.story_ai_provider import StubStoryProvider
from app.services.story_generation_service import StoryGenerationService
from app.services.story_points_calculator import StoryPointsCalculator
from app.models.requirement import Requirement
from app.models.impact_analysis import ImpactAnalysis
from app.models.user_story import UserStory
from app.core.config import Settings


def make_client_with_data():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    # Pre-insert source connection, requirement and analysis
    db = Session()
    seed_source_connection(db)
    _req_text = "Register with email"
    req = Requirement(
        id="req-endpoint-1",
        tenant_id=TEST_TENANT_ID,
        source_connection_id=TEST_CONNECTION_ID,
        requirement_text=_req_text,
        requirement_text_hash=hashlib.sha256(_req_text.encode()).hexdigest(),
        project_id="proj",
        intent="create_account",
        action="create",
        entity="user",
        feature_type="feature",
        priority="medium",
        business_domain="user_management",
        technical_scope="backend",
        estimated_complexity="MEDIUM",
        keywords='["user", "email"]',
        processing_time_seconds=1.0,
        created_at=datetime.now(timezone.utc),
    )
    analysis = ImpactAnalysis(
        id="ana-endpoint-1",
        tenant_id=TEST_TENANT_ID,
        source_connection_id=TEST_CONNECTION_ID,
        requirement="Register with email",
        risk_level="LOW",
        files_impacted=2,
        modules_impacted=1,
        analysis_summary="Two files",
        created_at=datetime.now(timezone.utc),
    )
    db.add(req)
    db.add(analysis)
    db.commit()
    db.close()

    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    def override() -> StoryGenerationService:
        db2 = Session()
        return StoryGenerationService(
            ai_generator=AIStoryGenerator(StubStoryProvider(), settings),
            requirement_repo=RequirementRepository(db2),
            impact_repo=ImpactAnalysisRepository(db2),
            story_repo=UserStoryRepository(db2),
            points_calculator=StoryPointsCalculator(),
            settings=settings,
        )

    app = apply_mock_auth(create_app())
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_story_service] = override
    return TestClient(app)


@pytest.fixture
def client():
    return make_client_with_data()


def _body(req_id="req-endpoint-1", ana_id="ana-endpoint-1", conn_id=TEST_CONNECTION_ID) -> dict:
    return {
        "requirement_id": req_id,
        "impact_analysis_id": ana_id,
        "project_id": "proj",
        "source_connection_id": conn_id,
    }


def test_generate_story_returns_200(client):
    response = client.post("/api/v1/generate-story", json=_body())
    assert response.status_code == 200


def test_response_contains_required_fields(client):
    response = client.post("/api/v1/generate-story", json=_body())
    data = response.json()
    assert "story_id" in data
    assert data["source_connection_id"] == TEST_CONNECTION_ID
    assert "title" in data
    assert "story_points" in data
    assert "risk_level" in data
    assert "generation_time_seconds" in data
    assert "request_id" in data


def test_response_ids_are_valid_uuids(client):
    response = client.post("/api/v1/generate-story", json=_body())
    assert response.status_code == 200
    data = response.json()
    uuid.UUID(data["story_id"])
    uuid.UUID(data["request_id"])


def test_nonexistent_requirement_returns_404(client):
    response = client.post("/api/v1/generate-story", json=_body(req_id="does-not-exist"))
    assert response.status_code == 404


def test_nonexistent_analysis_returns_404(client):
    response = client.post("/api/v1/generate-story", json=_body(ana_id="does-not-exist"))
    assert response.status_code == 404


def test_invalid_connection_returns_404(client):
    response = client.post("/api/v1/generate-story", json=_body(conn_id="does-not-exist"))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /stories/{story_id}
# ---------------------------------------------------------------------------

_KNOWN_STORY_ID = "story-get-test-1"
_KNOWN_STORY_CREATED_AT = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


def make_client_with_story():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    db = TestSession()
    seed_source_connection(db)
    db.add(UserStory(
        id=_KNOWN_STORY_ID,
        tenant_id=TEST_TENANT_ID,
        source_connection_id=TEST_CONNECTION_ID,
        requirement_id="req-get-1",
        impact_analysis_id="ana-get-1",
        project_id="proj-get",
        title="User Registration with Email Confirmation",
        story_description="As a user, I want to register with email so I can access the platform.",
        acceptance_criteria=json.dumps(["User can register", "Email is validated", "Confirmation sent"]),
        subtasks=json.dumps({"frontend": ["Create form"], "backend": ["Create endpoint", "Add validation", "Send email"], "configuration": []}),
        definition_of_done=json.dumps(["Code reviewed", "Tests passing", "Deployed"]),
        risk_notes=json.dumps(["External email dependency"]),
        story_points=5,
        risk_level="LOW",
        generation_time_seconds=1.23,
        created_at=_KNOWN_STORY_CREATED_AT,
    ))
    db.commit()
    db.close()

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app = apply_mock_auth(create_app())
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture(scope="module")
def story_client():
    return make_client_with_story()


def test_get_story_returns_full_details(story_client):
    response = story_client.get(f"/api/v1/stories/{_KNOWN_STORY_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["story_id"] == _KNOWN_STORY_ID
    assert data["source_connection_id"] == TEST_CONNECTION_ID
    assert data["requirement_id"] == "req-get-1"
    assert data["impact_analysis_id"] == "ana-get-1"
    assert data["project_id"] == "proj-get"
    assert data["title"] == "User Registration with Email Confirmation"
    assert data["story_points"] == 5
    assert data["risk_level"] == "LOW"
    assert isinstance(data["acceptance_criteria"], list)
    assert len(data["acceptance_criteria"]) == 3
    assert isinstance(data["subtasks"], dict)
    assert isinstance(data["subtasks"]["backend"], list)
    assert len(data["subtasks"]["backend"]) == 3
    assert isinstance(data["definition_of_done"], list)
    assert len(data["definition_of_done"]) == 3
    assert isinstance(data["risk_notes"], list)
    assert len(data["risk_notes"]) == 1
    assert data["created_at"].startswith("2025-01-15T10:30:00")


def test_get_story_returns_404_for_missing(story_client):
    response = story_client.get("/api/v1/stories/does-not-exist")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_story_acceptance_criteria_is_list(story_client):
    response = story_client.get(f"/api/v1/stories/{_KNOWN_STORY_ID}")
    assert response.status_code == 200
    criteria = response.json()["acceptance_criteria"]
    assert isinstance(criteria, list)
    assert all(isinstance(item, str) for item in criteria)

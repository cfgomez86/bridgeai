import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.database.session import Base
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
from app.core.config import Settings


def make_client_with_data():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    # Pre-insert requirement and analysis
    db = Session()
    req = Requirement(
        id="req-endpoint-1",
        requirement_text="Register with email",
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

    app = create_app()
    app.dependency_overrides[get_story_service] = override
    return TestClient(app)


@pytest.fixture
def client():
    return make_client_with_data()


def test_generate_story_returns_200(client):
    response = client.post(
        "/api/v1/generate-story",
        json={"requirement_id": "req-endpoint-1", "impact_analysis_id": "ana-endpoint-1", "project_id": "proj"},
    )
    assert response.status_code == 200


def test_response_contains_required_fields(client):
    response = client.post(
        "/api/v1/generate-story",
        json={"requirement_id": "req-endpoint-1", "impact_analysis_id": "ana-endpoint-1", "project_id": "proj"},
    )
    data = response.json()
    assert "story_id" in data
    assert "title" in data
    assert "story_points" in data
    assert "risk_level" in data
    assert "generation_time_seconds" in data
    assert "request_id" in data


def test_response_ids_are_valid_uuids(client):
    response = client.post(
        "/api/v1/generate-story",
        json={"requirement_id": "req-endpoint-1", "impact_analysis_id": "ana-endpoint-1", "project_id": "proj"},
    )
    assert response.status_code == 200
    data = response.json()
    uuid.UUID(data["story_id"])
    uuid.UUID(data["request_id"])


def test_nonexistent_requirement_returns_404(client):
    response = client.post(
        "/api/v1/generate-story",
        json={"requirement_id": "does-not-exist", "impact_analysis_id": "ana-endpoint-1", "project_id": "proj"},
    )
    assert response.status_code == 404


def test_nonexistent_analysis_returns_404(client):
    response = client.post(
        "/api/v1/generate-story",
        json={"requirement_id": "req-endpoint-1", "impact_analysis_id": "does-not-exist", "project_id": "proj"},
    )
    assert response.status_code == 404
